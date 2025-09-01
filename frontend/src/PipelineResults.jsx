import { useState, useEffect } from 'react';

const PipelineResults = ({ baseUrl = "" }) => {
  const [results, setResults] = useState({
    signals: null,
    newsScoreSignals: null,
    recommendations: null,
    loading: false,
    error: null
  });

  const fetchResults = async () => {
    setResults(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      // 並行獲取所有結果
      const [signalsRes, newsSignalsRes, recommendationsRes] = await Promise.allSettled([
        fetch(`${baseUrl}/api/signals/summary/?limit=10&days_back=7`),
        fetch(`${baseUrl}/api/signals/news-score-summary/?limit=10&lookback_hours=168`),
        fetch(`http://127.0.0.1:8001/api/recommendations/`)
      ]);

      const newResults = { loading: false, error: null };

      // 處理信號數據
      if (signalsRes.status === 'fulfilled' && signalsRes.value.ok) {
        newResults.signals = await signalsRes.value.json();
      }

      // 處理新聞分數信號數據
      if (newsSignalsRes.status === 'fulfilled' && newsSignalsRes.value.ok) {
        newResults.newsScoreSignals = await newsSignalsRes.value.json();
      }

      // 處理投資建議數據
      if (recommendationsRes.status === 'fulfilled' && recommendationsRes.value.ok) {
        newResults.recommendations = await recommendationsRes.value.json();
      }

      setResults(newResults);

    } catch (error) {
      console.error('Failed to fetch results:', error);
      setResults(prev => ({ 
        ...prev, 
        loading: false, 
        error: '獲取結果時發生錯誤' 
      }));
    }
  };

  useEffect(() => {
    fetchResults();
  }, [baseUrl]);

  if (results.loading) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="flex items-center justify-center space-x-2">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="text-gray-600">載入結果中...</span>
        </div>
      </div>
    );
  }

  if (results.error) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex">
            <div className="text-red-400">⚠️</div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">載入錯誤</h3>
              <p className="mt-1 text-sm text-red-700">{results.error}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">📊 流水線執行結果</h2>
        <button
          onClick={fetchResults}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 text-sm"
        >
          🔄 刷新結果
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 研究匹配信號結果 */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">📈 研究匹配信號</h3>
          
          {results.signals ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-blue-50 rounded-lg p-3">
                  <div className="text-sm font-medium text-blue-600">活躍公司</div>
                  <div className="text-xl font-bold text-blue-900">
                    {results.signals.summary?.active_companies || 0}
                  </div>
                </div>
                <div className="bg-green-50 rounded-lg p-3">
                  <div className="text-sm font-medium text-green-600">活躍行業</div>
                  <div className="text-xl font-bold text-green-900">
                    {results.signals.summary?.active_industries || 0}
                  </div>
                </div>
              </div>

              {/* 頂級正面公司 */}
              {results.signals.rankings?.top_positive_companies?.length > 0 && (
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">🔥 頂級正面公司</h4>
                  <div className="space-y-2">
                    {results.signals.rankings.top_positive_companies.slice(0, 3).map((company, index) => (
                      <div key={index} className="flex justify-between items-center p-2 bg-green-50 rounded">
                        <span className="font-medium text-green-800">{company.ticker}</span>
                        <span className="text-sm text-green-600">
                          {company.score > 0 ? '+' : ''}{company.score.toFixed(2)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-gray-500 text-center py-8">
              暫無研究匹配信號數據
            </div>
          )}
        </div>

        {/* 新聞分數信號結果 */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">📰 新聞分數信號</h3>
          
          {results.newsScoreSignals ? (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-purple-50 rounded-lg p-3">
                  <div className="text-sm font-medium text-purple-600">活躍公司</div>
                  <div className="text-xl font-bold text-purple-900">
                    {results.newsScoreSignals.summary?.active_companies || 0}
                  </div>
                </div>
                <div className="bg-orange-50 rounded-lg p-3">
                  <div className="text-sm font-medium text-orange-600">活躍行業</div>
                  <div className="text-xl font-bold text-orange-900">
                    {results.newsScoreSignals.summary?.active_industries || 0}
                  </div>
                </div>
              </div>

              {/* 頂級正面公司 */}
              {results.newsScoreSignals.rankings?.top_positive_companies?.length > 0 && (
                <div>
                  <h4 className="font-medium text-gray-700 mb-2">⭐ 新聞正面公司</h4>
                  <div className="space-y-2">
                    {results.newsScoreSignals.rankings.top_positive_companies.slice(0, 3).map((company, index) => (
                      <div key={index} className="flex justify-between items-center p-2 bg-blue-50 rounded">
                        <span className="font-medium text-blue-800">{company.ticker}</span>
                        <span className="text-sm text-blue-600">
                          {company.window_score > 0 ? '+' : ''}{parseFloat(company.window_score).toFixed(2)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-gray-500 text-center py-8">
              暫無新聞分數信號數據
            </div>
          )}
        </div>
      </div>

      {/* 投資建議結果 */}
      {results.recommendations && (
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">💡 投資建議</h3>
          
          {results.recommendations.items?.length > 0 ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-green-50 rounded-lg p-4">
                  <div className="text-sm font-medium text-green-600">總建議數</div>
                  <div className="text-2xl font-bold text-green-900">
                    {results.recommendations.count || results.recommendations.items.length}
                  </div>
                </div>
                <div className="bg-blue-50 rounded-lg p-4">
                  <div className="text-sm font-medium text-blue-600">平均評分</div>
                  <div className="text-2xl font-bold text-blue-900">
                    {(results.recommendations.items.reduce((sum, item) => sum + item.final, 0) / 
                      results.recommendations.items.length).toFixed(2)}
                  </div>
                </div>
                <div className="bg-purple-50 rounded-lg p-4">
                  <div className="text-sm font-medium text-purple-600">生成日期</div>
                  <div className="text-sm font-bold text-purple-900">
                    {results.recommendations.date || '未知'}
                  </div>
                </div>
              </div>

              {/* 頂級建議 */}
              <div>
                <h4 className="font-medium text-gray-700 mb-3">🏆 頂級投資建議</h4>
                <div className="overflow-x-auto">
                  <table className="min-w-full">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="text-left py-2 px-3 font-medium text-gray-700">排名</th>
                        <th className="text-left py-2 px-3 font-medium text-gray-700">股票</th>
                        <th className="text-left py-2 px-3 font-medium text-gray-700">最終評分</th>
                        <th className="text-left py-2 px-3 font-medium text-gray-700">相對強度</th>
                        <th className="text-left py-2 px-3 font-medium text-gray-700">新聞權重</th>
                        <th className="text-left py-2 px-3 font-medium text-gray-700">Stage2</th>
                      </tr>
                    </thead>
                    <tbody>
                      {results.recommendations.items.slice(0, 10).map((item, index) => (
                        <tr key={index} className="border-b border-gray-100">
                          <td className="py-2 px-3 text-gray-600">{item.rank}</td>
                          <td className="py-2 px-3 font-medium text-blue-600">{item.ticker}</td>
                          <td className="py-2 px-3 text-green-600 font-medium">
                            {item.final.toFixed(1)}
                          </td>
                          <td className="py-2 px-3 text-gray-700">
                            {item.rs.toFixed(1)}
                          </td>
                          <td className="py-2 px-3 text-gray-700">
                            {item.news_w.toFixed(2)}
                          </td>
                          <td className="py-2 px-3">
                            {item.stage2 ? (
                              <span className="text-green-600 font-bold">★</span>
                            ) : (
                              <span className="text-gray-400">-</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-gray-500 text-center py-8">
              暫無投資建議數據
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default PipelineResults;
