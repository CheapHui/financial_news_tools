import React, { useState, useEffect } from "react";

/**
 * 信號匯總儀表板 - 顯示最新的公司和行業信號排行榜
 */

// UI 組件
const cx = (...xs) => xs.filter(Boolean).join(" ");

const Card = ({ title, subtitle, right, children, className }) => (
  <div className={cx(
    "rounded-2xl border border-slate-200/60 bg-white/90 backdrop-blur-sm shadow-sm",
    "hover:shadow-lg hover:border-slate-300/60 transition-all duration-300",
    "hover:-translate-y-0.5",
    className
  )}>
    {(title || right) && (
      <div className="flex items-start justify-between p-6 pb-0">
        <div>
          {title && <h3 className="text-lg font-semibold text-slate-900 tracking-tight">{title}</h3>}
          {subtitle && <p className="text-sm text-slate-500 mt-1 font-medium">{subtitle}</p>}
        </div>
        {right}
      </div>
    )}
    <div className="p-6 pt-4">{children}</div>
  </div>
);

const ScoreBadge = ({ score }) => {
  const isPositive = score > 0;
  const isNegative = score < 0;
  const isNeutral = score === 0;
  
  return (
    <span className={cx(
      "inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold",
      isPositive && "bg-green-100 text-green-800",
      isNegative && "bg-red-100 text-red-800", 
      isNeutral && "bg-gray-100 text-gray-800"
    )}>
      {isPositive && "+"}
      {score.toFixed(4)}
    </span>
  );
};

const RankingList = ({ items, type, onItemClick }) => {
  if (!items || items.length === 0) {
    return (
      <div className="text-center py-8 text-slate-500">
        <p>暫無數據</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {items.map((item, index) => (
        <div 
          key={type === 'company' ? item.ticker : item.industry_id}
          className="flex items-center justify-between p-4 bg-slate-50/50 rounded-xl hover:bg-slate-100/50 transition-colors cursor-pointer"
          onClick={() => onItemClick && onItemClick(item)}
        >
          <div className="flex items-center space-x-4">
            <div className="flex items-center justify-center w-8 h-8 bg-white rounded-lg shadow-sm">
              <span className="text-sm font-bold text-slate-600">#{index + 1}</span>
            </div>
            <div>
              <div className="font-semibold text-slate-900">
                {type === 'company' ? item.ticker : item.industry_name}
              </div>
              {type === 'company' && (
                <div className="text-xs text-slate-500 truncate max-w-48">
                  {item.company_name}
                </div>
              )}
              <div className="text-xs text-slate-400">
                {item.top_news_count} 條相關新聞
              </div>
            </div>
          </div>
          <div className="text-right">
            <ScoreBadge score={item.score} />
            <div className="text-xs text-slate-400 mt-1">
              {new Date(item.window_end).toLocaleDateString('zh-TW')}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

const StatCard = ({ title, value, subtitle, color = "blue" }) => (
  <div className="bg-white/80 rounded-xl p-4 border border-slate-200/60">
    <div className="flex items-center space-x-3">
      <div className={cx(
        "w-10 h-10 rounded-lg flex items-center justify-center",
        color === "green" && "bg-green-100 text-green-600",
        color === "red" && "bg-red-100 text-red-600",
        color === "blue" && "bg-blue-100 text-blue-600",
        color === "gray" && "bg-gray-100 text-gray-600"
      )}>
        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
          <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" />
        </svg>
      </div>
      <div>
        <div className="text-2xl font-bold text-slate-900">{value}</div>
        <div className="text-sm text-slate-600">{title}</div>
        {subtitle && <div className="text-xs text-slate-400">{subtitle}</div>}
      </div>
    </div>
  </div>
);

export default function SignalsSummaryDashboard({ baseUrl = "" }) {
  const [summaryData, setSummaryData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);
  const [limit, setLimit] = useState(10);
  const [daysBack, setDaysBack] = useState(7);

  // 載入信號匯總數據
  const loadSummary = async () => {
    setLoading(true);
    setError("");
    
    try {
      const url = `${baseUrl}/api/signals/summary/?limit=${limit}&days_back=${daysBack}`;
      const res = await fetch(url);
      
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      }
      
      const data = await res.json();
      setSummaryData(data);
    } catch (err) {
      setError(err.message);
      setSummaryData(null);
    } finally {
      setLoading(false);
    }
  };

  // 初始載入和刷新
  useEffect(() => {
    loadSummary();
  }, [refreshKey, limit, daysBack]);

  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1);
  };

  const handleCompanyClick = (company) => {
    // 可以導向到具體公司的信號頁面
    console.log('點擊公司:', company);
  };

  const handleIndustryClick = (industry) => {
    // 可以導向到具體行業的信號頁面  
    console.log('點擊行業:', industry);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-slate-200/60 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-xl flex items-center justify-center">
                  <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                </div>
                <div>
                  <h1 className="text-xl font-bold text-slate-900">信號匯總儀表板</h1>
                  <p className="text-sm text-slate-600">實時監控市場信號趨勢</p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center space-x-3">
              <button
                onClick={handleRefresh}
                disabled={loading}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {loading ? "載入中..." : "刷新數據"}
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        {/* 控制面板 */}
        <Card title="查詢參數" className="mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                每類排行榜數量
              </label>
              <select 
                value={limit}
                onChange={(e) => setLimit(parseInt(e.target.value))}
                className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
              >
                <option value={5}>前 5 名</option>
                <option value={10}>前 10 名</option>
                <option value={20}>前 20 名</option>
                <option value={50}>前 50 名</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">
                時間範圍
              </label>
              <select
                value={daysBack}
                onChange={(e) => setDaysBack(parseInt(e.target.value))}
                className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
              >
                <option value={3}>最近 3 天</option>
                <option value={7}>最近 7 天</option>
                <option value={14}>最近 14 天</option>
                <option value={30}>最近 30 天</option>
              </select>
            </div>
          </div>
        </Card>

        {error && (
          <Card className="border-red-200 bg-red-50">
            <div className="text-red-800">
              <p className="font-semibold">載入失敗</p>
              <p className="text-sm mt-1">{error}</p>
            </div>
          </Card>
        )}

        {loading && (
          <Card>
            <div className="text-center py-8">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              <p className="mt-2 text-slate-600">載入中...</p>
            </div>
          </Card>
        )}

        {summaryData && (
          <>
            {/* 統計概覽 */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard 
                title="公司信號總數"
                value={summaryData.summary.company_stats.total_signals}
                subtitle={`最近 ${daysBack} 天`}
                color="blue"
              />
              <StatCard 
                title="正面信號"
                value={summaryData.summary.company_stats.positive_signals}
                subtitle={`平均: ${summaryData.summary.company_stats.avg_score.toFixed(3)}`}
                color="green"
              />
              <StatCard 
                title="負面信號"
                value={summaryData.summary.company_stats.negative_signals}
                subtitle={`最低: ${summaryData.summary.company_stats.max_negative_score.toFixed(3)}`}
                color="red"
              />
              <StatCard 
                title="行業信號"
                value={summaryData.summary.industry_stats.total_signals}
                subtitle={`覆蓋行業數`}
                color="gray"
              />
            </div>

            {/* 排行榜 */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              {/* 公司正面信號排行榜 */}
              <Card 
                title="📈 最強勢公司" 
                subtitle={`正面信號排行榜 (前 ${limit} 名)`}
              >
                <RankingList 
                  items={summaryData.rankings.top_positive_companies}
                  type="company"
                  onItemClick={handleCompanyClick}
                />
              </Card>

              {/* 公司負面信號排行榜 */}
              <Card 
                title="📉 最弱勢公司" 
                subtitle={`負面信號排行榜 (前 ${limit} 名)`}
              >
                <RankingList 
                  items={summaryData.rankings.top_negative_companies}
                  type="company"
                  onItemClick={handleCompanyClick}
                />
              </Card>

              {/* 行業正面信號排行榜 */}
              <Card 
                title="🚀 最熱門行業" 
                subtitle={`正面信號排行榜 (前 ${limit} 名)`}
              >
                <RankingList 
                  items={summaryData.rankings.top_positive_industries}
                  type="industry"
                  onItemClick={handleIndustryClick}
                />
              </Card>

              {/* 行業負面信號排行榜 */}
              <Card 
                title="❄️ 最冷門行業" 
                subtitle={`負面信號排行榜 (前 ${limit} 名)`}
              >
                <RankingList 
                  items={summaryData.rankings.top_negative_industries}
                  type="industry"
                  onItemClick={handleIndustryClick}
                />
              </Card>
            </div>

            {/* 詳細統計 */}
            <Card title="📊 詳細統計信息">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div>
                  <h4 className="font-semibold text-slate-900 mb-4">公司信號統計</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-slate-600">總信號數:</span>
                      <span className="font-medium">{summaryData.summary.company_stats.total_signals}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-600">正面信號:</span>
                      <span className="font-medium text-green-600">{summaryData.summary.company_stats.positive_signals}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-600">負面信號:</span>
                      <span className="font-medium text-red-600">{summaryData.summary.company_stats.negative_signals}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-600">平均分數:</span>
                      <span className="font-medium">{summaryData.summary.company_stats.avg_score.toFixed(4)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-600">最高正面分數:</span>
                      <span className="font-medium text-green-600">+{summaryData.summary.company_stats.max_positive_score.toFixed(4)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-600">最低負面分數:</span>
                      <span className="font-medium text-red-600">{summaryData.summary.company_stats.max_negative_score.toFixed(4)}</span>
                    </div>
                  </div>
                </div>
                
                <div>
                  <h4 className="font-semibold text-slate-900 mb-4">行業信號統計</h4>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-slate-600">總信號數:</span>
                      <span className="font-medium">{summaryData.summary.industry_stats.total_signals}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-600">正面信號:</span>
                      <span className="font-medium text-green-600">{summaryData.summary.industry_stats.positive_signals}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-600">負面信號:</span>
                      <span className="font-medium text-red-600">{summaryData.summary.industry_stats.negative_signals}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-600">平均分數:</span>
                      <span className="font-medium">{summaryData.summary.industry_stats.avg_score.toFixed(4)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-600">最高正面分數:</span>
                      <span className="font-medium text-green-600">+{summaryData.summary.industry_stats.max_positive_score.toFixed(4)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-600">最低負面分數:</span>
                      <span className="font-medium text-red-600">{summaryData.summary.industry_stats.max_negative_score.toFixed(4)}</span>
                    </div>
                  </div>
                </div>
              </div>
            </Card>
          </>
        )}

        <footer className="text-center py-6 border-t border-slate-200/60 bg-white/50 rounded-2xl backdrop-blur-sm">
          <div className="text-sm text-slate-500 space-y-1">
            <p className="font-medium">💡 信號匯總說明</p>
            <p className="text-xs">
              信號分數基於新聞內容與研究報告的相似度計算，結合時間衰減和極性分析
            </p>
            <p className="text-xs">
              正分數表示正面信號，負分數表示負面信號，分數絕對值越大表示信號越強
            </p>
          </div>
        </footer>
      </main>
    </div>
  );
}
