import { useState, useEffect, useRef } from 'react';
import PipelineResults from './PipelineResults';

const PipelineController = ({ baseUrl = "" }) => {
  const [pipelineStatus, setPipelineStatus] = useState({
    is_running: false,
    current_step: null,
    total_steps: 0,
    completed_steps: 0,
    progress: 0,
    start_time: null,
    end_time: null,
    duration: null,
    error: null,
    logs: []
  });

  const [pipelineConfig, setPipelineConfig] = useState({
    // 新聞攝取參數
    skip_ingest: false,
    max_news: 40,
    allow_langs: "en,zh",
    
    // 處理參數
    since_hours: 24,
    model: "deepseek-reasoner",
    half_life: 72,
    lookback_hours: 168,
    apply_overall_when_missing: false,
    
    // 建議生成參數
    skip_recommendations: false,
    benchmark: "SPY",
    min_cap: 20000000000,
    universe_limit: 800,
    rs_threshold: 70.0,
    alpha: 0.2,
    k: 1.0,
    save_top: 200
  });

  const [showAdvanced, setShowAdvanced] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const statusIntervalRef = useRef(null);

  // 獲取流水線狀態
  const fetchPipelineStatus = async () => {
    try {
      const response = await fetch(`http://127.0.0.1:8001/api/pipeline/status/`);
      if (response.ok) {
        const data = await response.json();
        setPipelineStatus(data);
      }
    } catch (error) {
      console.error('Failed to fetch pipeline status:', error);
    }
  };

  // 啟動流水線
  const startPipeline = async () => {
    setIsLoading(true);
    try {
      const response = await fetch(`http://127.0.0.1:8001/api/pipeline/start/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(pipelineConfig),
      });

      const data = await response.json();
      if (response.ok) {
        // 立即開始輪詢狀態
        startStatusPolling();
      } else {
        alert(`啟動失敗: ${data.error}`);
      }
    } catch (error) {
      console.error('Failed to start pipeline:', error);
      alert('啟動流水線時發生錯誤');
    } finally {
      setIsLoading(false);
    }
  };

  // 停止流水線
  const stopPipeline = async () => {
    try {
      const response = await fetch(`http://127.0.0.1:8001/api/pipeline/stop/`, {
        method: 'POST',
      });

      const data = await response.json();
      if (!response.ok) {
        alert(`停止失敗: ${data.error}`);
      }
    } catch (error) {
      console.error('Failed to stop pipeline:', error);
      alert('停止流水線時發生錯誤');
    }
  };

  // 清除日誌
  const clearLogs = async () => {
    try {
      const response = await fetch(`http://127.0.0.1:8001/api/pipeline/clear-logs/`, {
        method: 'POST',
      });

      if (response.ok) {
        fetchPipelineStatus();
      }
    } catch (error) {
      console.error('Failed to clear logs:', error);
    }
  };

  // 開始狀態輪詢
  const startStatusPolling = () => {
    if (statusIntervalRef.current) {
      clearInterval(statusIntervalRef.current);
    }
    
    statusIntervalRef.current = setInterval(() => {
      fetchPipelineStatus();
    }, 2000); // 每2秒更新一次
  };

  // 停止狀態輪詢
  const stopStatusPolling = () => {
    if (statusIntervalRef.current) {
      clearInterval(statusIntervalRef.current);
      statusIntervalRef.current = null;
    }
  };

  // 組件掛載時獲取初始狀態
  useEffect(() => {
    fetchPipelineStatus();
    return () => stopStatusPolling();
  }, []);

  // 根據運行狀態控制輪詢
  useEffect(() => {
    if (pipelineStatus.is_running) {
      startStatusPolling();
    } else {
      stopStatusPolling();
    }
  }, [pipelineStatus.is_running]);

  // 格式化時間
  const formatDuration = (seconds) => {
    if (!seconds) return '--';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}分${secs}秒`;
  };

  // 格式化時間戳
  const formatTimestamp = (timestamp) => {
    if (!timestamp) return '--';
    return new Date(timestamp).toLocaleString('zh-CN');
  };

  return (
    <div className="space-y-6">
      {/* 流水線控制面板 */}
      <div className="bg-white rounded-lg shadow-lg p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">🚀 流水線控制中心</h2>
        <div className="flex items-center space-x-2">
          {pipelineStatus.is_running && (
            <div className="flex items-center space-x-2 text-blue-600">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
              <span className="text-sm font-medium">運行中</span>
            </div>
          )}
        </div>
      </div>

      {/* 狀態卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-blue-50 rounded-lg p-4">
          <div className="text-sm font-medium text-blue-600">狀態</div>
          <div className="text-lg font-bold text-blue-900">
            {pipelineStatus.is_running ? '運行中' : '空閒'}
          </div>
        </div>
        
        <div className="bg-green-50 rounded-lg p-4">
          <div className="text-sm font-medium text-green-600">進度</div>
          <div className="text-lg font-bold text-green-900">
            {pipelineStatus.progress}%
          </div>
        </div>
        
        <div className="bg-purple-50 rounded-lg p-4">
          <div className="text-sm font-medium text-purple-600">步驟</div>
          <div className="text-lg font-bold text-purple-900">
            {pipelineStatus.completed_steps}/{pipelineStatus.total_steps}
          </div>
        </div>
        
        <div className="bg-orange-50 rounded-lg p-4">
          <div className="text-sm font-medium text-orange-600">耗時</div>
          <div className="text-lg font-bold text-orange-900">
            {formatDuration(pipelineStatus.duration)}
          </div>
        </div>
      </div>

      {/* 進度條 */}
      {pipelineStatus.total_steps > 0 && (
        <div className="space-y-2">
          <div className="flex justify-between text-sm text-gray-600">
            <span>執行進度</span>
            <span>{pipelineStatus.progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div 
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${pipelineStatus.progress}%` }}
            ></div>
          </div>
        </div>
      )}

      {/* 錯誤信息 */}
      {pipelineStatus.error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <div className="text-red-400">⚠️</div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">執行錯誤</h3>
              <p className="mt-1 text-sm text-red-700">{pipelineStatus.error}</p>
            </div>
          </div>
        </div>
      )}

      {/* 配置面板 */}
      <div className="border border-gray-200 rounded-lg p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">流水線配置</h3>
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="text-sm text-blue-600 hover:text-blue-800"
          >
            {showAdvanced ? '隱藏高級選項' : '顯示高級選項'}
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* 基本配置 */}
          <div className="space-y-4">
            <h4 className="font-medium text-gray-700">基本設置</h4>
            
            <div>
              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={pipelineConfig.skip_ingest}
                  onChange={(e) => setPipelineConfig(prev => ({
                    ...prev,
                    skip_ingest: e.target.checked
                  }))}
                  disabled={pipelineStatus.is_running}
                />
                <span className="text-sm text-gray-700">跳過新聞攝取</span>
              </label>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                處理時間範圍 (小時)
              </label>
              <input
                type="number"
                value={pipelineConfig.since_hours}
                onChange={(e) => setPipelineConfig(prev => ({
                  ...prev,
                  since_hours: parseInt(e.target.value) || 24
                }))}
                disabled={pipelineStatus.is_running}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                min="1"
                max="168"
              />
            </div>

            <div>
              <label className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  checked={pipelineConfig.skip_recommendations}
                  onChange={(e) => setPipelineConfig(prev => ({
                    ...prev,
                    skip_recommendations: e.target.checked
                  }))}
                  disabled={pipelineStatus.is_running}
                />
                <span className="text-sm text-gray-700">跳過投資建議生成</span>
              </label>
            </div>
          </div>

          {/* 高級配置 */}
          {showAdvanced && (
            <div className="space-y-4">
              <h4 className="font-medium text-gray-700">高級設置</h4>
              
              {!pipelineConfig.skip_ingest && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    新聞攝取數量
                  </label>
                  <input
                    type="number"
                    value={pipelineConfig.max_news}
                    onChange={(e) => setPipelineConfig(prev => ({
                      ...prev,
                      max_news: parseInt(e.target.value) || 40
                    }))}
                    disabled={pipelineStatus.is_running}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                    min="1"
                    max="100"
                  />
                </div>
              )}

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  AI 模型
                </label>
                <select
                  value={pipelineConfig.model}
                  onChange={(e) => setPipelineConfig(prev => ({
                    ...prev,
                    model: e.target.value
                  }))}
                  disabled={pipelineStatus.is_running}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                >
                  <option value="deepseek-reasoner">DeepSeek Reasoner</option>
                  <option value="deepseek-chat">DeepSeek Chat</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  半衰期 (小時)
                </label>
                <input
                  type="number"
                  value={pipelineConfig.half_life}
                  onChange={(e) => setPipelineConfig(prev => ({
                    ...prev,
                    half_life: parseInt(e.target.value) || 72
                  }))}
                  disabled={pipelineStatus.is_running}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
                  min="1"
                  max="720"
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 控制按鈕 */}
      <div className="flex space-x-4">
        <button
          onClick={startPipeline}
          disabled={pipelineStatus.is_running || isLoading}
          className={`px-6 py-2 rounded-lg font-medium ${
            pipelineStatus.is_running || isLoading
              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
              : 'bg-blue-600 text-white hover:bg-blue-700'
          }`}
        >
          {isLoading ? '啟動中...' : '🚀 啟動流水線'}
        </button>

        <button
          onClick={stopPipeline}
          disabled={!pipelineStatus.is_running}
          className={`px-6 py-2 rounded-lg font-medium ${
            !pipelineStatus.is_running
              ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
              : 'bg-red-600 text-white hover:bg-red-700'
          }`}
        >
          ⏹️ 停止流水線
        </button>

        <button
          onClick={fetchPipelineStatus}
          className="px-6 py-2 bg-gray-600 text-white rounded-lg font-medium hover:bg-gray-700"
        >
          🔄 刷新狀態
        </button>

        <button
          onClick={clearLogs}
          className="px-6 py-2 bg-orange-600 text-white rounded-lg font-medium hover:bg-orange-700"
        >
          🗑️ 清除日誌
        </button>
      </div>

      {/* 執行日誌 */}
      {pipelineStatus.logs && pipelineStatus.logs.length > 0 && (
        <div className="border border-gray-200 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">執行日誌</h3>
          <div className="bg-gray-50 rounded-lg p-3 max-h-64 overflow-y-auto">
            <div className="space-y-1 text-sm font-mono">
              {pipelineStatus.logs.map((log, index) => (
                <div key={index} className={`flex space-x-2 ${
                  log.level === 'ERROR' ? 'text-red-600' :
                  log.level === 'WARNING' ? 'text-orange-600' :
                  log.level === 'SUCCESS' ? 'text-green-600' :
                  'text-gray-700'
                }`}>
                  <span className="text-gray-400">
                    {new Date(log.timestamp).toLocaleTimeString('zh-CN')}
                  </span>
                  <span>{log.message}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* 執行歷史 */}
      <div className="border border-gray-200 rounded-lg p-4">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">執行信息</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <span className="font-medium text-gray-600">開始時間:</span>
            <span className="ml-2 text-gray-900">
              {formatTimestamp(pipelineStatus.start_time)}
            </span>
          </div>
          <div>
            <span className="font-medium text-gray-600">結束時間:</span>
            <span className="ml-2 text-gray-900">
              {formatTimestamp(pipelineStatus.end_time)}
            </span>
          </div>
        </div>
      </div>
      </div>

      {/* 結果顯示 */}
      <PipelineResults baseUrl={baseUrl} />
    </div>
  );
};

export default PipelineController;
