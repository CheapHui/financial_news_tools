from django.core.management.base import BaseCommand
from django.core.management import call_command

class Command(BaseCommand):
    help = "完整新聞分析流水線: ingest_rss -> embed_news -> link_news_entities -> score_news -> rollup_signals -> build_recommendations"

    def add_arguments(self, parser):
        # 新聞攝取參數
        parser.add_argument("--max-news", type=int, default=40, help="每個RSS源最多攝取新聞數量")
        parser.add_argument("--feed", type=str, action="append", help="指定RSS源URL (可多次使用)")
        parser.add_argument("--allow-langs", type=str, default="en,zh", help="允許的語言")
        parser.add_argument("--skip-ingest", action="store_true", help="跳過新聞攝取步驟")
        
        # 新聞處理參數
        parser.add_argument("--since-hours", type=int, default=24, help="處理最近N小時的新聞")
        parser.add_argument("--model", type=str, default="deepseek-reasoner", help="AI模型名稱")
        parser.add_argument("--half-life", type=int, default=72, help="新聞分數時間衰減半衰期(小時)")
        parser.add_argument("--lookback-hours", type=int, default=24*7, help="信號聚合回看時間(小時)")
        parser.add_argument("--apply-overall-when-missing", action="store_true", help="當無精準匹配時使用整體情感")
        
        # 建議生成參數
        parser.add_argument("--benchmark", type=str, default="SPY", help="基準指數")
        parser.add_argument("--min-cap", type=float, default=20e9, help="最小市值過濾")
        parser.add_argument("--universe-limit", type=int, default=800, help="股票池最大數量")
        parser.add_argument("--rs-threshold", type=float, default=70.0, help="相對強度閾值")
        parser.add_argument("--alpha", type=float, default=0.2, help="新聞權重係數")
        parser.add_argument("--k", type=float, default=1.0, help="tanh壓縮係數")
        parser.add_argument("--save-top", type=int, default=200, help="保存前N個建議")
        
        # 控制選項
        parser.add_argument("--skip-recommendations", action="store_true", help="跳過建議生成步驟")
        parser.add_argument("--verbose", action="store_true", help="詳細輸出")

    def handle(self, *args, **opts):
        sh = opts["since_hours"]
        days_back = max(1, sh // 24)  # 將小時轉換為天數
        verbose = opts["verbose"]
        
        # 計算總步驟數
        total_steps = 0
        if not opts["skip_ingest"]:
            total_steps += 1  # ingest_rss
        total_steps += 4  # embed + link + score + rollup
        if not opts["skip_recommendations"]:
            total_steps += 1  # build_recommendations
        
        self.stdout.write(self.style.SUCCESS(f"🚀 開始執行完整新聞分析流水線 (共 {total_steps} 步驟)"))
        
        if verbose:
            self.stdout.write(f"參數設定:")
            if not opts["skip_ingest"]:
                self.stdout.write(f"  - 新聞攝取數量: {opts['max_news']} 條/源")
                self.stdout.write(f"  - 允許語言: {opts['allow_langs']}")
            self.stdout.write(f"  - 新聞處理時間範圍: {sh} 小時 ({days_back} 天)")
            self.stdout.write(f"  - AI 模型: {opts['model']}")
            self.stdout.write(f"  - 半衰期: {opts['half_life']} 小時")
            self.stdout.write(f"  - 信號回看: {opts['lookback_hours']} 小時")
            if not opts["skip_recommendations"]:
                self.stdout.write(f"  - 基準指數: {opts['benchmark']}")
                self.stdout.write(f"  - 最小市值: {opts['min_cap']:,.0f}")
        
        current_step = 0
        
        # 步驟 0: 新聞攝取 (可選)
        if not opts["skip_ingest"]:
            current_step += 1
            self.stdout.write(self.style.WARNING(f"[{current_step}/{total_steps}] 📰 ingest_rss (max={opts['max_news']})"))
            try:
                ingest_args = {
                    "max": opts["max_news"],
                    "allow_langs": opts["allow_langs"]
                }
                # 如果指定了特定的 RSS 源
                if opts["feed"]:
                    for feed_url in opts["feed"]:
                        call_command("ingest_rss", feed=feed_url, **ingest_args)
                else:
                    call_command("ingest_rss", **ingest_args)
                    
                if verbose:
                    self.stdout.write(self.style.SUCCESS("  ✅ 新聞攝取完成"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ❌ 新聞攝取失敗: {e}"))
                return
        
        # 步驟: 嵌入向量生成
        current_step += 1
        self.stdout.write(self.style.WARNING(f"[{current_step}/{total_steps}] 📊 embed_news (days_back={days_back})"))
        try:
            call_command("embed_news", days_back=days_back)
            if verbose:
                self.stdout.write(self.style.SUCCESS("  ✅ 嵌入向量生成完成"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ 嵌入向量生成失敗: {e}"))
            return

        # 步驟: 實體連結
        current_step += 1
        self.stdout.write(self.style.WARNING(f"[{current_step}/{total_steps}] 🔗 link_news_entities (days_back={days_back})"))
        try:
            call_command("link_news_entities", days_back=days_back)
            if verbose:
                self.stdout.write(self.style.SUCCESS("  ✅ 實體連結完成"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ 實體連結失敗: {e}"))
            return

        # 步驟: 新聞分數計算
        current_step += 1
        self.stdout.write(self.style.WARNING(f"[{current_step}/{total_steps}] 🤖 score_news (since_hours={sh}, model={opts['model']})"))
        try:
            call_command("score_news",
                         since_hours=sh,
                         model=opts["model"],
                         half_life=opts["half_life"])
            if verbose:
                self.stdout.write(self.style.SUCCESS("  ✅ 新聞分數計算完成"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ 新聞分數計算失敗: {e}"))
            return

        # 步驟: 信號聚合
        current_step += 1
        self.stdout.write(self.style.WARNING(f"[{current_step}/{total_steps}] 📈 rollup_signals (lookback_hours={opts['lookback_hours']})"))
        try:
            call_command("rollup_signals",
                         lookback_hours=opts["lookback_hours"],
                         apply_overall_when_missing=opts["apply_overall_when_missing"])
            if verbose:
                self.stdout.write(self.style.SUCCESS("  ✅ 信號聚合完成"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ 信號聚合失敗: {e}"))
            return

        # 步驟: 建議生成 (可選)
        if not opts["skip_recommendations"]:
            current_step += 1
            self.stdout.write(self.style.WARNING(f"[{current_step}/{total_steps}] 💡 build_recommendations"))
            try:
                call_command("build_recommendations",
                            benchmark=opts["benchmark"],
                            min_cap=opts["min_cap"],
                            universe_limit=opts["universe_limit"],
                            rs_threshold=opts["rs_threshold"],
                            alpha=opts["alpha"],
                            k=opts["k"],
                            save_top=opts["save_top"])
                if verbose:
                    self.stdout.write(self.style.SUCCESS("  ✅ 投資建議生成完成"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ❌ 投資建議生成失敗: {e}"))
                self.stdout.write(self.style.WARNING("  💡 提示: 可能需要安裝 pandas 和 yfinance: pip install pandas yfinance"))
                return

        self.stdout.write(self.style.SUCCESS("🎉 完整新聞分析流水線執行完成！"))
        
        # 顯示結果摘要
        self.stdout.write("\n" + "="*50)
        self.stdout.write("📊 執行結果摘要:")
        if not opts["skip_ingest"]:
            self.stdout.write("  - 新聞攝取: 已完成")
        self.stdout.write("  - 新聞嵌入向量: 已更新")
        self.stdout.write("  - 實體連結: 已更新")  
        self.stdout.write("  - 新聞分數: 已計算")
        self.stdout.write("  - 信號聚合: 已完成")
        if not opts["skip_recommendations"]:
            self.stdout.write("  - 投資建議: 已生成")
        self.stdout.write("="*50)