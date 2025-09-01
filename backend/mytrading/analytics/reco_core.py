import math
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, List, Tuple

# ---------- RS 百分位（對基準的相對回報，做全市場百分位） ----------

def _period_ret(close: pd.Series, lookback: int) -> float:
    if len(close) < lookback + 1 or close.iloc[-lookback-1] <= 0:
        return np.nan
    return float(close.iloc[-1] / close.iloc[-lookback-1] - 1.0)

def _relative_ret(stock_close: pd.Series, bench_close: pd.Series, lookback: int) -> float:
    rs = _period_ret(stock_close, lookback)
    rb = _period_ret(bench_close, lookback)
    if np.isnan(rs) or np.isnan(rb):
        return np.nan
    # 相對回報： (1+rs)/(1+rb) - 1
    return (1.0 + rs) / (1.0 + rb) - 1.0

def _percentiles(values: Dict[str, float]) -> Dict[str, float]:
    series = pd.Series(values, dtype=float)
    valid = series.dropna()
    if valid.empty:
        return {k: np.nan for k in values.keys()}
    ranks = valid.rank(method="min", pct=True) * 100.0
    out = {k: float(ranks.get(k, np.nan)) for k in values.keys()}
    return out

def rs_percentile_universe(
    closes: Dict[str, pd.Series], bench_close: pd.Series,
    weights=(0.2, 0.3, 0.5), windows=(21, 63, 126)
) -> Dict[str, Dict[str, float]]:
    """
    回傳：
    {
      ticker: {
        "p1m": 0~100, "p3m": 0~100, "p6m": 0~100,
        "rs100": 綜合 0~100
      }
    }
    """
    rel_1 = {t: _relative_ret(c, bench_close, windows[0]) for t, c in closes.items()}
    rel_3 = {t: _relative_ret(c, bench_close, windows[1]) for t, c in closes.items()}
    rel_6 = {t: _relative_ret(c, bench_close, windows[2]) for t, c in closes.items()}

    p1 = _percentiles(rel_1)
    p3 = _percentiles(rel_3)
    p6 = _percentiles(rel_6)

    out = {}
    for t in closes.keys():
        p1m = p1.get(t, np.nan)
        p3m = p3.get(t, np.nan)
        p6m = p6.get(t, np.nan)
        # 權重：1/3/6m = 0.2/0.3/0.5（可調）
        arr = np.array([p1m, p3m, p6m], dtype=float)
        w   = np.array(weights, dtype=float)
        rs100 = float(np.nansum(arr * w) / np.nansum(w[~np.isnan(arr)])) if not np.all(np.isnan(arr)) else np.nan
        out[t] = {"p1m": p1m, "p3m": p3m, "p6m": p6m, "rs100": rs100}
    return out

# ---------- Minervini Stage 2 判定 ----------

def minervini_stage2(
    close: pd.Series, high: pd.Series, low: pd.Series,
    rs100: float, rs_threshold: float = 70.0
) -> Tuple[bool, Dict[str, bool]]:
    """
    常見條件（可按你口味細修）：
    1) Price > MA50 > MA150 > MA200
    2) MA200 最近 ~1個月向上（> 前21日）
    3) Price >= 1.25 * 52W Low（離底 >=25%）
    4) Price >= 0.75 * 52W High（距頂 <=25%）
    5) RS >= 70
    """
    if len(close) < 260:
        return False, {"enough_history": False}

    ma50  = close.rolling(50).mean()
    ma150 = close.rolling(150).mean()
    ma200 = close.rolling(200).mean()

    last = int(close.index[-1] == close.index[-1])  # just to placate linters
    c  = float(close.iloc[-1])
    m50  = float(ma50.iloc[-1])
    m150 = float(ma150.iloc[-1])
    m200 = float(ma200.iloc[-1])
    m200_prev = float(ma200.iloc[-21]) if not math.isnan(ma200.iloc[-21]) else m200

    hh_52 = float(high.rolling(252).max().iloc[-1])
    ll_52 = float(low.rolling(252).min().iloc[-1])

    conds = {
        "ma_stack": (c > m50 > m150 > m200),
        "ma200_up": (m200 > m200_prev),
        "dist_from_low_52w": (c >= 1.25 * ll_52) if ll_52 > 0 else False,
        "near_high_52w": (c >= 0.75 * hh_52) if hh_52 > 0 else False,
        "rs_threshold": (rs100 >= rs_threshold),
        "enough_history": True,
    }
    passed = all(conds.values())
    return passed, conds

# ---------- 新聞權重（把你 rollup 的 window_score 壓縮再轉成乘數） ----------

def news_weight_factor(window_score: float, alpha: float = 0.2, k: float = 1.0) -> float:
    """
    將 window_score（可正可負）經 tanh 壓縮到 [-1,1]，
    再做乘數： 1 + α * tanh(k * score) ，α 預設 0.2（±20% 調幅）
    """
    x = math.tanh(k * float(window_score))
    return float(1.0 + alpha * x)