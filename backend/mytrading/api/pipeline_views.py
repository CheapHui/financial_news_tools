import json
import threading
import time
from datetime import datetime, timezone
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.management import call_command
from django.utils import timezone as django_timezone
import logging

logger = logging.getLogger(__name__)

# 全局變量存儲流水線狀態
pipeline_status = {
    "is_running": False,
    "current_step": None,
    "total_steps": 0,
    "completed_steps": 0,
    "start_time": None,
    "end_time": None,
    "error": None,
    "results": {},
    "logs": []
}

def add_log(message, level="INFO"):
    """添加日誌到狀態中"""
    global pipeline_status
    timestamp = datetime.now(timezone.utc).isoformat()
    log_entry = {
        "timestamp": timestamp,
        "level": level,
        "message": message
    }
    pipeline_status["logs"].append(log_entry)
    # 保持最多 100 條日誌
    if len(pipeline_status["logs"]) > 100:
        pipeline_status["logs"] = pipeline_status["logs"][-100:]

def run_pipeline_async(params):
    """異步運行流水線"""
    global pipeline_status
    
    try:
        pipeline_status["is_running"] = True
        pipeline_status["start_time"] = datetime.now(timezone.utc).isoformat()
        pipeline_status["error"] = None
        pipeline_status["logs"] = []
        pipeline_status["results"] = {}
        
        # 計算總步驟數
        total_steps = 0
        if not params.get("skip_ingest", False):
            total_steps += 1
        total_steps += 4  # embed + link + score + rollup
        if not params.get("skip_recommendations", False):
            total_steps += 1
        
        pipeline_status["total_steps"] = total_steps
        pipeline_status["completed_steps"] = 0
        
        add_log("🚀 開始執行完整新聞分析流水線")
        
        # 構建命令參數
        cmd_args = {
            "since_hours": params.get("since_hours", 24),
            "model": params.get("model", "deepseek-reasoner"),
            "half_life": params.get("half_life", 72),
            "lookback_hours": params.get("lookback_hours", 168),
            "verbose": True
        }
        
        # 新聞攝取參數
        if not params.get("skip_ingest", False):
            cmd_args["max_news"] = params.get("max_news", 40)
            cmd_args["allow_langs"] = params.get("allow_langs", "en,zh")
        else:
            cmd_args["skip_ingest"] = True
            
        # 建議生成參數
        if params.get("skip_recommendations", False):
            cmd_args["skip_recommendations"] = True
        else:
            cmd_args.update({
                "benchmark": params.get("benchmark", "SPY"),
                "min_cap": params.get("min_cap", 20e9),
                "universe_limit": params.get("universe_limit", 800),
                "rs_threshold": params.get("rs_threshold", 70.0),
                "alpha": params.get("alpha", 0.2),
                "k": params.get("k", 1.0),
                "save_top": params.get("save_top", 200)
            })
        
        if params.get("apply_overall_when_missing", False):
            cmd_args["apply_overall_when_missing"] = True
        
        add_log(f"參數設定: {json.dumps(cmd_args, indent=2, ensure_ascii=False)}")
        
        # 執行流水線
        call_command("process_news_pipeline", **cmd_args)
        
        pipeline_status["end_time"] = datetime.now(timezone.utc).isoformat()
        pipeline_status["completed_steps"] = pipeline_status["total_steps"]
        add_log("🎉 流水線執行完成！", "SUCCESS")
        
    except Exception as e:
        error_msg = f"流水線執行失敗: {str(e)}"
        pipeline_status["error"] = error_msg
        pipeline_status["end_time"] = datetime.now(timezone.utc).isoformat()
        add_log(error_msg, "ERROR")
        logger.exception("Pipeline execution failed")
        
    finally:
        pipeline_status["is_running"] = False

@csrf_exempt
@require_http_methods(["POST"])
def start_pipeline(request):
    """啟動流水線"""
    global pipeline_status
    
    if pipeline_status["is_running"]:
        return JsonResponse({
            "success": False,
            "error": "流水線已在運行中"
        }, status=400)
    
    try:
        # 解析請求參數
        if request.content_type == 'application/json':
            params = json.loads(request.body)
        else:
            params = {}
        
        # 啟動異步執行
        thread = threading.Thread(target=run_pipeline_async, args=(params,))
        thread.daemon = True
        thread.start()
        
        return JsonResponse({
            "success": True,
            "message": "流水線已啟動"
        })
        
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": f"啟動失敗: {str(e)}"
        }, status=500)

@require_http_methods(["GET"])
def pipeline_status_api(request):
    """獲取流水線狀態"""
    global pipeline_status
    
    # 計算進度百分比
    progress = 0
    if pipeline_status["total_steps"] > 0:
        progress = (pipeline_status["completed_steps"] / pipeline_status["total_steps"]) * 100
    
    # 計算運行時間
    duration = None
    if pipeline_status["start_time"]:
        start = datetime.fromisoformat(pipeline_status["start_time"].replace('Z', '+00:00'))
        end_time = pipeline_status["end_time"]
        if end_time:
            end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        else:
            end = datetime.now(timezone.utc)
        duration = int((end - start).total_seconds())
    
    return JsonResponse({
        "is_running": pipeline_status["is_running"],
        "current_step": pipeline_status["current_step"],
        "total_steps": pipeline_status["total_steps"],
        "completed_steps": pipeline_status["completed_steps"],
        "progress": round(progress, 1),
        "start_time": pipeline_status["start_time"],
        "end_time": pipeline_status["end_time"],
        "duration": duration,
        "error": pipeline_status["error"],
        "results": pipeline_status["results"],
        "logs": pipeline_status["logs"][-20:]  # 只返回最近 20 條日誌
    })

@require_http_methods(["POST"])
def stop_pipeline(request):
    """停止流水線（注意：這只是標記停止，實際命令可能仍在運行）"""
    global pipeline_status
    
    if not pipeline_status["is_running"]:
        return JsonResponse({
            "success": False,
            "error": "流水線未在運行"
        }, status=400)
    
    pipeline_status["is_running"] = False
    pipeline_status["error"] = "用戶手動停止"
    pipeline_status["end_time"] = datetime.now(timezone.utc).isoformat()
    add_log("用戶手動停止流水線", "WARNING")
    
    return JsonResponse({
        "success": True,
        "message": "流水線已停止"
    })

@require_http_methods(["POST"])
def clear_pipeline_logs(request):
    """清除流水線日誌"""
    global pipeline_status
    
    pipeline_status["logs"] = []
    
    return JsonResponse({
        "success": True,
        "message": "日誌已清除"
    })
