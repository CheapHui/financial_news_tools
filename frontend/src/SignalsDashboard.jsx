import React, { useMemo, useState, useEffect } from "react";
import SignalsSummaryDashboard from "./SignalsSummaryDashboard";
import NewsScoreSignalsDashboard from "./NewsScoreSignalsDashboard";
import PipelineController from "./PipelineController";

/**
 * MyTrading — Signals Dashboard (refined UI)
 * - Polished Tailwind UI, cleaner layout, grouped matches by object_type
 * - Works with your reverse proxy (/api → Django)
 * - Entry: <SignalsDashboard baseUrl="">, or set to "http://localhost:8000" for dev
 */

// ---------- Small UI primitives ----------
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

const Field = ({ label, hint, children }) => (
  <label className="block group">
    <div className="flex items-center gap-2 mb-2">
      <span className="text-sm font-semibold text-slate-700 tracking-tight">{label}</span>
      {hint && <span className="text-xs text-slate-400">{hint}</span>}
    </div>
    {children}
  </label>
);

const Input = (props) => (
  <input
    {...props}
    className={cx(
      "w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm",
      "outline-none ring-0 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20",
      "placeholder:text-slate-400 transition-all duration-200",
      "hover:border-slate-300"
    )}
  />
);

const Pill = ({ children, tone = "gray" }) => {
  const tones = {
    gray: "bg-slate-100 text-slate-700 border-slate-200",
    blue: "bg-blue-50 text-blue-700 border-blue-200 shadow-sm",
    green: "bg-emerald-50 text-emerald-700 border-emerald-200 shadow-sm",
    red: "bg-rose-50 text-rose-700 border-rose-200 shadow-sm",
    amber: "bg-amber-50 text-amber-700 border-amber-200 shadow-sm",
    violet: "bg-violet-50 text-violet-700 border-violet-200 shadow-sm",
  };
  return (
    <span className={cx(
      "px-3 py-1.5 rounded-full text-xs font-medium border transition-all duration-200",
      "hover:scale-105 cursor-default",
      tones[tone] || tones.gray
    )}>
      {children}
    </span>
  );
};

const Spinner = () => (
  <div className="inline-block h-5 w-5 animate-spin rounded-full border-[2px] border-slate-200 border-t-blue-600" />
);

const JSONBlock = ({ data }) => (
  <pre className="text-xs bg-slate-50 rounded-xl p-4 overflow-auto max-h-80 border border-slate-200 font-mono leading-relaxed">{JSON.stringify(data, null, 2)}</pre>
);

const ScoreBar = ({ value }) => (
  <div className="h-3 w-full rounded-full bg-slate-100 overflow-hidden shadow-inner">
    <div
      className="h-full bg-gradient-to-r from-emerald-500 to-blue-600 rounded-full transition-all duration-500 ease-out"
      // 顯示分數數值（百分比形式，保留兩位小數）
      style={{ width: `${Math.max(0, Math.min(1, value || 0)) * 100}%` }}
      >
    </div>
  </div>
);

const ScoreText = ({ value }) => (
  <span className="ml-2 text-xs text-slate-600 font-mono">
    {(typeof value === "number" && !isNaN(value) ? (value * 100).toFixed(2) : "0.00") + "%"}
  </span>
);



// ---------- Data hooks ----------
function useFetchJson(url, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  useEffect(() => {
    let cancelled = false;
    async function go() {
      if (!url) return;
      setLoading(true); setError(null);
      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const j = await res.json();
        if (!cancelled) setData(j);
      } catch (e) {
        if (!cancelled) setError(e);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    go();
    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  return { data, loading, error };
}

// ---------- Views ----------
const TYPE_TONE = {
  company_profile: "blue",
  company_risk: "red",
  company_catalyst: "green",
  company_thesis: "violet",
  industry_profile: "amber",
  industry_player: "gray",
};

// Embedding Quality View
function EmbeddingQualityView({ baseUrl }) {
  const { data, loading, error } = useFetchJson(`${baseUrl}/api/evals/quality`, [`${baseUrl}/api/evals/quality`]);
  
  const MetricCard = ({ label, value, format = 'percent' }) => (
    <div className="bg-white/60 rounded-xl p-4 border border-slate-200/60">
      <div className="text-xs text-slate-500 mb-1 font-medium">{label}</div>
      <div className="text-lg font-bold text-slate-900">
        {format === 'percent' ? `${(value * 100).toFixed(1)}%` : value}
      </div>
      <div className="mt-2">
        <ScoreBar value={value} />
        <div className="text-xs text-slate-700 mt-1">Score: <ScoreText value={value} /></div>
      </div>
    </div>
  );
  
  return (
    <Card 
      title="Embedding Quality Metrics" 
      subtitle="系統評估指標概覽" 
      right={loading ? <Spinner/> : null}
    >
      {error && <div className="text-rose-600 text-sm mb-4">{String(error)}</div>}
      {data && (
        <div className="space-y-6">
          {/* Overall Quality */}
          <div className="flex items-center gap-4">
            <Pill tone={data.overall_quality?.color || 'gray'}>
              Overall: {data.overall_quality?.grade || 'Unknown'}
            </Pill>
            <div className="text-sm text-slate-600">
              Score: <span className="font-bold">{(data.overall_quality?.score * 100).toFixed(1)}%</span>
            </div>
            <div className="text-xs text-slate-400">
              Last eval: {new Date(data.last_evaluation).toLocaleString()}
            </div>
          </div>
          
          {/* Metrics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard label="Recall@1" value={data.metrics?.recall_at_1 || 0} />
            <MetricCard label="Recall@3" value={data.metrics?.recall_at_3 || 0} />
            <MetricCard label="Recall@5" value={data.metrics?.recall_at_5 || 0} />
            <MetricCard label="Recall@10" value={data.metrics?.recall_at_10 || 0} />
          </div>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard label="NDCG@1" value={data.metrics?.ndcg_at_1 || 0} />
            <MetricCard label="NDCG@3" value={data.metrics?.ndcg_at_3 || 0} />
            <MetricCard label="NDCG@5" value={data.metrics?.ndcg_at_5 || 0} />
            <MetricCard label="NDCG@10" value={data.metrics?.ndcg_at_10 || 0} />
          </div>
          
          {/* Stats */}
          <div className="bg-slate-50 rounded-xl p-4 border border-slate-200">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <div className="text-slate-500">Total Docs</div>
                <div className="font-bold text-slate-900">{data.stats?.total_docs || 0}</div>
              </div>
              <div>
                <div className="text-slate-500">Total Queries</div>
                <div className="font-bold text-slate-900">{data.stats?.total_queries || 0}</div>
              </div>
              <div>
                <div className="text-slate-500">Avg First Rank</div>
                <div className="font-bold text-slate-900">{data.stats?.avg_first_relevant_rank || 0}</div>
              </div>
              <div>
                <div className="text-slate-500">Evaluations</div>
                <div className="font-bold text-slate-900">{data.stats?.evaluation_count || 0}</div>
              </div>
            </div>
          </div>
        </div>
      )}
      {!data && !loading && (
        <div className="text-slate-500 text-center py-8">
          <div className="text-4xl mb-2">📊</div>
          <div>No evaluation data available</div>
        </div>
      )}
    </Card>
  );
}

// URL Analysis View
function URLAnalysisView({ baseUrl }) {
  const [url, setUrl] = useState('');
  const [topk, setTopk] = useState(10);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const handleAnalyzeUrl = async () => {
    if (!url.trim()) {
      setError('请输入有效的URL');
      return;
    }
    
    setLoading(true);
    setError(null);
    setAnalysisResult(null);
    
    try {
      const response = await fetch(`${baseUrl}/api/news/analyze-url`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          url: url.trim(),
          topk: topk
        })
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }
      
      const result = await response.json();
      setAnalysisResult(result);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };
  
  const grouped = useMemo(() => {
    if (!analysisResult?.matches) return {};
    const g = {};
    analysisResult.matches.forEach(m => {
      const t = m.object_type;
      g[t] = g[t] || [];
      g[t].push(m);
    });
    return g;
  }, [analysisResult]);
  
  return (
    <Card title="URL News Analysis" subtitle="输入新闻URL进行内容分析和匹配">
      <div className="space-y-6">
        {/* Input Section */}
        <div className="space-y-4">
          <Field label="新闻URL">
            <Input
              value={url}
              onChange={e => setUrl(e.target.value)}
              placeholder="https://example.com/news-article"
              disabled={loading}
            />
          </Field>
          
          <div className="flex items-center gap-4">
            <Field label="匹配数量">
              <Input
                type="number"
                value={topk}
                onChange={e => setTopk(parseInt(e.target.value) || 10)}
                placeholder="10"
                min="1"
                max="50"
                disabled={loading}
                className="w-24"
              />
            </Field>
            
            <button
              onClick={handleAnalyzeUrl}
              disabled={loading || !url.trim()}
              className={cx(
                "px-8 py-3 rounded-xl text-sm font-semibold transition-all duration-200",
                "bg-blue-600 text-white hover:bg-blue-700 hover:shadow-lg",
                "disabled:opacity-50 disabled:cursor-not-allowed",
                "flex items-center gap-2"
              )}
            >
              {loading ? (
                <>
                  <Spinner />
                  <span>分析中...</span>
                </>
              ) : (
                <>
                  🔍
                  <span>分析URL</span>
                </>
              )}
            </button>
          </div>
        </div>
        
        {/* Error Display */}
        {error && (
          <div className="text-rose-600 text-sm bg-rose-50 rounded-xl p-4 border border-rose-200">
            <div className="font-medium mb-1">分析失败</div>
            <div>{error}</div>
          </div>
        )}
        
        {/* Results Display */}
        {analysisResult && (
          <div className="space-y-6 border-t border-slate-200 pt-6">
            {/* Summary Info */}
            <div className="bg-slate-50 rounded-xl p-4 border border-slate-200">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <div className="text-slate-500 mb-1">语言</div>
                  <div className="font-bold text-slate-900">{analysisResult.language}</div>
                </div>
                <div>
                  <div className="text-slate-500 mb-1">字数</div>
                  <div className="font-bold text-slate-900">{analysisResult.word_count.toLocaleString()}</div>
                </div>
                <div>
                  <div className="text-slate-500 mb-1">文本块数</div>
                  <div className="font-bold text-slate-900">{analysisResult.total_chunks}</div>
                </div>
                <div>
                  <div className="text-slate-500 mb-1">匹配数</div>
                  <div className="font-bold text-slate-900">{analysisResult.matches.length}</div>
                </div>
              </div>
              
              <div className="mt-4 pt-4 border-t border-slate-200">
                <div className="text-slate-500 text-xs mb-2">标题预览</div>
                <div className="text-sm text-slate-700 leading-relaxed">{analysisResult.title}</div>
              </div>
              
              <div className="mt-3 pt-3 border-t border-slate-200">
                <div className="text-slate-500 text-xs mb-2">原始URL</div>
                <a 
                  href={analysisResult.url} 
                  target="_blank" 
                  rel="noreferrer"
                  className="text-blue-600 hover:text-blue-700 text-sm underline break-all"
                >
                  {analysisResult.url}
                </a>
              </div>
            </div>
            
            {/* Type Distribution */}
            {Object.keys(grouped).length > 0 && (
              <div>
                <div className="text-sm font-medium mb-3">匹配类型分布</div>
                <div className="flex flex-wrap gap-2">
                  {Object.keys(grouped).sort().map(t => (
                    <Pill key={t} tone={TYPE_TONE[t] || "gray"}>
                      {t} · {grouped[t].length}
                    </Pill>
                  ))}
                </div>
              </div>
            )}
            
            {/* Matches Grid */}
            <div>
              <div className="text-sm font-medium mb-4">匹配结果 (Top {analysisResult.matches.length})</div>
              <div className="grid md:grid-cols-2 gap-6">
                {analysisResult.matches.map((m, i) => (
                  <div key={i} className={cx(
                    "rounded-2xl border border-slate-200/60 p-5 bg-white/90 backdrop-blur-sm shadow-sm",
                    "hover:border-slate-300/60 hover:shadow-md transition-all duration-300",
                    "hover:-translate-y-0.5 group"
                  )}>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <Pill tone={TYPE_TONE[m.object_type] || "gray"}>{m.object_type}</Pill>
                        <span className="text-sm font-semibold text-slate-700">#{m.object_id}</span>
                      </div>
                      <div className="w-24">
                        <ScoreBar value={m.score} />
                        <div className="text-xs text-slate-600 mt-1 text-left">
                          <ScoreText value={m.score} />
                        </div>
                      </div>
                    </div>
                    
                    <div className="text-xs text-slate-500 mb-3 font-medium">
                      ticker: <span className="text-slate-700">{m.ticker || "-"}</span> ｜ 
                      industry: <span className="text-slate-700">{m.industry || "-"}</span>
                    </div>
                    
                    <div className="text-sm leading-relaxed text-slate-600 mb-3">
                      <div className="font-medium text-slate-700 mb-1">研究内容预览:</div>
                      <div className="line-clamp-3">{m.preview || "(no preview)"}</div>
                    </div>
                    
                    {m.source_chunk_preview && (
                      <div className="text-sm leading-relaxed text-slate-600 mb-3 border-t border-slate-200 pt-3">
                        <div className="font-medium text-slate-700 mb-1">匹配的原文片段 (块 #{m.source_chunk_idx}):</div>
                        <div className="bg-slate-50 rounded-lg p-3 text-xs line-clamp-4">{m.source_chunk_preview}</div>
                      </div>
                    )}
                    
                    <div className="text-xs text-slate-400 font-mono">ref_chunk_id: {m.ref_chunk_id}</div>
                  </div>
                ))}
              </div>
            </div>
            
            {/* Raw JSON for debugging */}
            <details>
              <summary className="cursor-pointer text-sm text-gray-600">原始JSON数据</summary>
              <JSONBlock data={analysisResult} />
            </details>
          </div>
        )}
      </div>
    </Card>
  );
}

// Quick Evaluation View
function QuickEvalView({ baseUrl }) {
  const [queryText, setQueryText] = useState('');
  const [docTexts, setDocTexts] = useState('');
  const [relevantIndices, setRelevantIndices] = useState('0');
  const [evalResult, setEvalResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const handleQuickEval = async () => {
    if (!queryText.trim() || !docTexts.trim()) {
      setError('請輸入查詢文本和文檔文本');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const docs = docTexts.split('\n').filter(line => line.trim());
      const indices = relevantIndices.split(',').map(i => parseInt(i.trim())).filter(i => !isNaN(i));
      
      const response = await fetch(`${baseUrl}/api/evals/quick`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query_text: queryText,
          doc_texts: docs,
          relevant_doc_indices: indices
        })
      });
      
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const result = await response.json();
      setEvalResult(result);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <Card title="Quick Embedding Evaluation" subtitle="快速測試 embedding 效果">
      <div className="space-y-4">
        <Field label="查詢文本">
          <Input
            value={queryText}
            onChange={e => setQueryText(e.target.value)}
            placeholder="輸入要搜索的查詢文本..."
          />
        </Field>
        
        <Field label="文檔文本" hint="每行一個文檔">
          <textarea
            className={cx(
              "w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm",
              "outline-none ring-0 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20",
              "placeholder:text-slate-400 transition-all duration-200",
              "hover:border-slate-300 min-h-[120px]"
            )}
            value={docTexts}
            onChange={e => setDocTexts(e.target.value)}
            placeholder="文檔1內容\n文檔2內容\n文檔3內容..."
          />
        </Field>
        
        <Field label="相關文檔索引" hint="以逗號分隔，從0開始">
          <Input
            value={relevantIndices}
            onChange={e => setRelevantIndices(e.target.value)}
            placeholder="0,2,3"
          />
        </Field>
        
        <button
          onClick={handleQuickEval}
          disabled={loading}
          className={cx(
            "w-full rounded-xl px-6 py-3 text-sm font-semibold transition-all duration-200",
            "bg-blue-600 text-white hover:bg-blue-700 hover:shadow-lg",
            "disabled:opacity-50 disabled:cursor-not-allowed"
          )}
        >
          {loading ? <Spinner /> : '開始評估'}
        </button>
        
        {error && (
          <div className="text-rose-600 text-sm bg-rose-50 rounded-xl p-3 border border-rose-200">
            {error}
          </div>
        )}
        
        {evalResult && (
          <div className="space-y-4 border-t border-slate-200 pt-4">
            <div className="flex items-center gap-3">
              <Pill tone={evalResult.quality_metrics?.quality_color || 'gray'}>
                {evalResult.quality_metrics?.quality_grade || 'Unknown'}
              </Pill>
              <div className="text-sm text-slate-600">
                評估時間: {new Date(evalResult.timestamp).toLocaleString()}
              </div>
            </div>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {Object.entries(evalResult.summary?.macro_recall_at_k || {}).map(([k, v]) => (
                <div key={k} className="bg-white/60 rounded-lg p-3 border border-slate-200/60">
                  <div className="text-xs text-slate-500 mb-1">Recall@{k}</div>
                  <div className="text-sm font-bold">{(v * 100).toFixed(1)}%</div>
                  <ScoreBar value={v} />
                </div>
              ))}
            </div>
            
            {evalResult.query_result?.top_10 && (
              <div>
                <div className="text-sm font-medium mb-2">Top 10 Results:</div>
                <div className="flex flex-wrap gap-2">
                  {evalResult.query_result.top_10.map((docId, i) => (
                    <Pill key={i} tone={i < 3 ? 'blue' : 'gray'}>
                      #{i+1}: {docId}
                    </Pill>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </Card>
  );
}

function MatchesView({ baseUrl, newsId, topk }) {
  const url = newsId ? `${baseUrl}/api/news/${newsId}/matches?topk=${topk||10}` : null;
  const { data, loading, error } = useFetchJson(url, [url]);

  const grouped = useMemo(() => {
    const g = {};
    (data?.matches || []).forEach(m => {
      const t = m.object_type;
      g[t] = g[t] || [];
      g[t].push(m);
    });
    return g;
  }, [data]);

  return (
    <Card title="News ↔ Research Matches" subtitle={url || "輸入 News ID 後查詢"} right={loading ? <Spinner/> : null}>
      {error && <div className="text-rose-600 text-sm mb-2">{String(error)}</div>}
      {!data && !loading && <div className="text-gray-500">請輸入 News ID 然後查詢。</div>}
      {data && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <Pill tone="gray">news_id: {data.news_id}</Pill>
            <Pill tone="gray">topk: {data.topk}</Pill>
          </div>
          <div className="text-sm text-gray-700">{data.title}</div>

          {/* grouped chips */}
          <div className="flex flex-wrap gap-2">
            {Object.keys(grouped).sort().map(t => (
              <Pill key={t} tone={TYPE_TONE[t] || "gray"}>{t} · {grouped[t].length}</Pill>
            ))}
          </div>

          <div className="grid md:grid-cols-2 gap-6">
            {(data.matches || []).map((m, i) => (
              <div key={i} className={cx(
                "rounded-2xl border border-slate-200/60 p-5 bg-white/90 backdrop-blur-sm shadow-sm",
                "hover:border-slate-300/60 hover:shadow-md transition-all duration-300",
                "hover:-translate-y-0.5 group"
              )}>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <Pill tone={TYPE_TONE[m.object_type] || "gray"}>{m.object_type}</Pill>
                    <span className="text-sm font-semibold text-slate-700">#{m.object_id}</span>
                  </div>
                  <div className="w-24">
                    <ScoreBar value={m.score} />
                    <div className="text-xs text-slate-600 mt-1 text-left">
                      <ScoreText value={m.score} />
                    </div>
                  </div>
                </div>
                <div className="text-xs text-slate-500 mb-3 font-medium">
                  ticker: <span className="text-slate-700">{m.ticker || "-"}</span> ｜ 
                  industry: <span className="text-slate-700">{m.industry || "-"}</span>
                </div>
                <div className="text-sm leading-relaxed text-slate-600 line-clamp-4 mb-3">
                  {m.preview || "(no preview)"}
                </div>
                <div className="text-xs text-slate-400 font-mono">ref_chunk_id: {m.ref_chunk_id}</div>
              </div>
            ))}
          </div>

          <details>
            <summary className="cursor-pointer text-sm text-gray-600">Raw JSON</summary>
            <JSONBlock data={data} />
          </details>
        </div>
      )}
    </Card>
  );
}

function CompanySignalView({ baseUrl, ticker }) {
  const url = ticker ? `${baseUrl}/api/companies/${encodeURIComponent(ticker)}/signals` : null;
  const { data, loading, error } = useFetchJson(url, [url]);
  return (
    <Card title="Company Signal" subtitle={url || "輸入 Ticker"} right={loading ? <Spinner/> : null}>
      {error && <div className="text-rose-600 text-sm mb-2">{String(error)}</div>}
      {!data && !loading && <div className="text-gray-500">輸入 Ticker（如 TSM）</div>}
      {data && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <Pill tone="blue">{data.ticker}</Pill>
            <Pill tone="gray">company_id: {data.company_id}</Pill>
            <Pill tone="gray">{data.name}</Pill>
          </div>
          {!data.signal ? (
            <div className="text-gray-500">No signal found.</div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="w-48"><ScoreBar value={data.signal.score} /></div>
                <span className="text-sm text-gray-700">{data.signal.score?.toFixed(3)}</span>
              </div>
              <div className="text-xs text-gray-500">
                {new Date(data.signal.window_start).toLocaleDateString()} → {new Date(data.signal.window_end).toLocaleDateString()}
              </div>
              <div>
                <div className="font-medium mb-1">Top News</div>
                <ul className="list-disc pl-5 text-sm">
                  {data.signal.top_news?.map((n) => (
                    <li key={n.id} className="mb-1">
                      <a className="underline text-blue-600" href={n.url} target="_blank" rel="noreferrer">{n.title}</a>
                      <span className="text-gray-500 ml-2">({new Date(n.published_at).toLocaleString()})</span>
                    </li>
                  ))}
                </ul>
              </div>
              <details>
                <summary className="cursor-pointer text-sm text-gray-600">Details (first 100)</summary>
                <JSONBlock data={data.signal.details?.slice(0,100)} />
              </details>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

function IndustrySignalView({ baseUrl, industryId }) {
  const url = industryId ? `${baseUrl}/api/industries/${industryId}/signals` : null;
  const { data, loading, error } = useFetchJson(url, [url]);
  return (
    <Card title="Industry Signal" subtitle={url || "輸入 Industry ID"} right={loading ? <Spinner/> : null}>
      {error && <div className="text-rose-600 text-sm mb-2">{String(error)}</div>}
      {!data && !loading && <div className="text-gray-500">輸入 Industry ID（如 1）</div>}
      {data && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <Pill tone="amber">industry_id: {data.industry_id}</Pill>
            <Pill tone="gray">{data.industry}</Pill>
          </div>
          {!data.signal ? (
            <div className="text-gray-500">No signal found.</div>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="w-48"><ScoreBar value={data.signal.score} /></div>
                <span className="text-sm text-gray-700">{data.signal.score?.toFixed(3)}</span>
              </div>
              <div className="text-xs text-gray-500">
                {new Date(data.signal.window_start).toLocaleDateString()} → {new Date(data.signal.window_end).toLocaleDateString()}
              </div>
              <div>
                <div className="font-medium mb-1">Top News</div>
                <ul className="list-disc pl-5 text-sm">
                  {data.signal.top_news?.map((n) => (
                    <li key={n.id} className="mb-1">
                      <a className="underline text-blue-600" href={n.url} target="_blank" rel="noreferrer">{n.title}</a>
                      <span className="text-gray-500 ml-2">({new Date(n.published_at).toLocaleString()})</span>
                    </li>
                  ))}
                </ul>
              </div>
              <details>
                <summary className="cursor-pointer text-sm text-gray-600">Details (first 100)</summary>
                <JSONBlock data={data.signal.details?.slice(0,100)} />
              </details>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

export default function SignalsDashboard({ baseUrl = "" }) {
  const [newsId, setNewsId] = useState("");
  const [topk, setTopk] = useState(10);
  const [ticker, setTicker] = useState("TSM");
  const [industryId, setIndustryId] = useState("");
  const [activeTab, setActiveTab] = useState("pipeline"); // "pipeline", "news-score", "summary", "signals", "evaluation", or "url-analysis"

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-indigo-50">
      {/* Professional Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-slate-200/60 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-xl flex items-center justify-center">
                  <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-slate-900 tracking-tight">MyTrading</h1>
                  <p className="text-sm text-slate-600">Signals Dashboard</p>
                </div>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-xs text-slate-500 bg-slate-100 px-3 py-1 rounded-full">
                baseUrl: <code className="text-slate-700">{baseUrl || "/"}</code>
              </div>
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" title="Live"></div>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-8 space-y-8">
        
                    {/* Tab Navigation */}
            <section>
          <div className="flex items-center gap-4 border-b border-slate-200">
            <button
              onClick={() => setActiveTab("signals")}
              className={cx(
                "px-6 py-3 text-sm font-semibold border-b-2 transition-all duration-200 whitespace-nowrap",
                activeTab === "signals" 
                  ? "border-blue-600 text-blue-600" 
                  : "border-transparent text-slate-600 hover:text-slate-900"
              )}
            >
              📊 信號查詢
            </button>
            <button
              onClick={() => setActiveTab("evaluation")}
              className={cx(
                "px-6 py-3 text-sm font-semibold border-b-2 transition-all duration-200 whitespace-nowrap",
                activeTab === "evaluation" 
                  ? "border-blue-600 text-blue-600" 
                  : "border-transparent text-slate-600 hover:text-slate-900"
              )}
            >
              🔍 嵌入評估
            </button>
            <button
              onClick={() => setActiveTab("url-analysis")}
              className={cx(
                "px-6 py-3 text-sm font-semibold border-b-2 transition-all duration-200 whitespace-nowrap",
                activeTab === "url-analysis" 
                  ? "border-blue-600 text-blue-600" 
                  : "border-transparent text-slate-600 hover:text-slate-900"
              )}
            >
              🌐 URL 分析
            </button>
          </div>
        </section>

                    {activeTab === "pipeline" && (
              <PipelineController baseUrl={baseUrl} />
            )}

            {activeTab === "news-score" && (
              <NewsScoreSignalsDashboard baseUrl={baseUrl} />
            )}

        {activeTab === "summary" && (
          <SignalsSummaryDashboard baseUrl={baseUrl} />
        )}

        {activeTab === "signals" && (
          <>
            {/* Controls Section */}
            <section className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="w-1 h-6 bg-gradient-to-b from-blue-600 to-indigo-600 rounded-full"></div>
                <h2 className="text-xl font-bold text-slate-900">控制面板</h2>
              </div>
          
              <div className="grid md:grid-cols-3 gap-6">
                <Card title="News → Matches" subtitle="新聞匹配查詢">
                  <div className="grid grid-cols-2 gap-4">
                    <Field label="News ID">
                      <Input 
                        value={newsId} 
                        onChange={e=>setNewsId(e.target.value)} 
                        placeholder="輸入新聞 ID" 
                      />
                    </Field>
                    <Field label="TopK">
                      <Input 
                        type="number" 
                        value={topk} 
                        onChange={e=>setTopk(parseInt(e.target.value||"10",10))} 
                        placeholder="10"
                      />
                    </Field>
                  </div>
                </Card>
                
                <Card title="Company Signal" subtitle="公司信號查詢">
                  <Field label="Ticker Symbol">
                    <Input 
                      value={ticker} 
                      onChange={e=>setTicker(e.target.value.toUpperCase())} 
                      placeholder="輸入股票代碼 (如: TSM)" 
                    />
                  </Field>
                </Card>
                
                <Card title="Industry Signal" subtitle="行業信號查詢">
                  <Field label="Industry ID">
                    <Input 
                      value={industryId} 
                      onChange={e=>setIndustryId(e.target.value)} 
                      placeholder="輸入行業 ID" 
                    />
                  </Field>
                </Card>
              </div>
            </section>

            {/* Results Section */}
            <section className="space-y-6">
              <div className="flex items-center gap-3">
                <div className="w-1 h-6 bg-gradient-to-b from-emerald-600 to-blue-600 rounded-full"></div>
                <h2 className="text-xl font-bold text-slate-900">分析結果</h2>
              </div>
              
              <div className="grid gap-8">
                {/* News Matches - Full Width */}
                <div className="w-full">
                  <MatchesView baseUrl={baseUrl} newsId={newsId} topk={topk} />
                </div>
                
                {/* Company & Industry Signals - Side by Side */}
                <div className="grid md:grid-cols-2 gap-8">
                  <CompanySignalView baseUrl={baseUrl} ticker={ticker} />
                  <IndustrySignalView baseUrl={baseUrl} industryId={industryId} />
                </div>
              </div>
            </section>
          </>
        )}

        {activeTab === "evaluation" && (
          <>
            {/* Embedding Evaluation Section */}
            <section className="space-y-6">
              <div className="flex items-center gap-3">
                <div className="w-1 h-6 bg-gradient-to-b from-violet-600 to-blue-600 rounded-full"></div>
                <h2 className="text-xl font-bold text-slate-900">Embedding 評估</h2>
              </div>
              
              <div className="grid gap-8">
                {/* Quality Overview */}
                <div className="w-full">
                  <EmbeddingQualityView baseUrl={baseUrl} />
                </div>
                
                {/* Quick Evaluation */}
                <div className="w-full">
                  <QuickEvalView baseUrl={baseUrl} />
                </div>
              </div>
            </section>
          </>
        )}

        {activeTab === "url-analysis" && (
          <>
            {/* URL Analysis Section */}
            <section className="space-y-6">
              <div className="flex items-center gap-3">
                <div className="w-1 h-6 bg-gradient-to-b from-emerald-600 to-blue-600 rounded-full"></div>
                <h2 className="text-xl font-bold text-slate-900">URL 新闻分析</h2>
              </div>
              
              <div className="grid gap-8">
                {/* URL Analysis Tool */}
                <div className="w-full">
                  <URLAnalysisView baseUrl={baseUrl} />
                </div>
              </div>
            </section>
          </>
        )}

        <footer className="text-center py-6 border-t border-slate-200/60 bg-white/50 rounded-2xl backdrop-blur-sm">
          <div className="text-sm text-slate-500 space-y-1">
            <p className="font-medium">💡 使用溫馨提示</p>
            <p className="text-xs">
              已配置 Nginx 反代 <code className="bg-slate-100 px-2 py-0.5 rounded text-slate-700">/api</code>，
              <code className="bg-slate-100 px-2 py-0.5 rounded text-slate-700">baseUrl</code> 保持空白即可。
            </p>
            <p className="text-xs">
              如需直連 Django，請設置 baseUrl 為 
              <code className="bg-slate-100 px-2 py-0.5 rounded text-slate-700">http://localhost:8000</code>
            </p>
          </div>
        </footer>
      </main>
    </div>
  );
}
