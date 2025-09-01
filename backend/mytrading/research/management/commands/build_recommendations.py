from django.core.management.base import BaseCommand
from django.utils import timezone
from collections import defaultdict
from decimal import Decimal
import pandas as pd
import yfinance as yf
import math

from reference.models import Company
from research.models import AnalyticsCompanySignal
from analytics.models import AnalyticsRecommendation
from analytics.reco_core import rs_percentile_universe, minervini_stage2, news_weight_factor

# --------- 實用：分批抓價，避免 yfinance 連接過多 ---------

def fetch_prices_yf(tickers, period="400d", interval="1d", batch=80):
    """
    回傳：
    prices[ticker] = DataFrame(columns=[Open, High, Low, Close, Volume])
    """
    prices = {}
    tickers = [t for t in tickers if t]  # 清理空字串
    for i in range(0, len(tickers), batch):
        chunk = tickers[i:i+batch]
        df = yf.download(chunk, period=period, interval=interval, auto_adjust=True, group_by="ticker", threads=True, progress=False)
        # yfinance 會有單 ticker / 多 ticker 兩種結構
        if isinstance(df.columns, pd.MultiIndex):
            for t in chunk:
                if t in df.columns.levels[0]:
                    sub = df[t].dropna()
                    if not sub.empty:
                        prices[t] = sub
        else:
            # 單 ticker
            t = chunk[0]
            sub = df.dropna()
            if not sub.empty:
                prices[t] = sub
    return prices

class Command(BaseCommand):
    help = "Compute RS ranking & Minervini Stage 2; merge with news rollup to produce recommendations"

    def add_arguments(self, parser):
        parser.add_argument("--benchmark", type=str, default="SPY")
        parser.add_argument("--min-cap", type=float, default=20e9, help="最少市值（如 model 有 market_cap）")
        parser.add_argument("--universe-limit", type=int, default=800, help="最多股票數（防止超時）")
        parser.add_argument("--rs-threshold", type=float, default=70.0)
        parser.add_argument("--alpha", type=float, default=0.2, help="新聞權重 α，乘數 = 1 + α*tanh(k*x)")
        parser.add_argument("--k", type=float, default=1.0, help="新聞權重 tanh 壓縮係數")
        parser.add_argument("--save-top", type=int, default=200, help="最多保存 top N（Stage2 優先）")

    def handle(self, *args, **opts):
        today = timezone.now().date()

        # 1) 構建 Universe
        qs = Company.objects.all()
        if hasattr(Company, "is_active"):
            qs = qs.filter(is_active=True)
        if hasattr(Company, "market_cap") and opts["min_cap"] > 0:
            qs = qs.filter(market_cap__gte=Decimal(str(opts["min_cap"])))
        tickers = list(qs.values_list("ticker", flat=True))[: opts["universe_limit"]]

        if not tickers:
            self.stderr.write("No tickers in universe")
            return

        # 2) 取價（股票 + 基準）
        self.stdout.write(f"Downloading prices for {len(tickers)} tickers...")
        prices = fetch_prices_yf(tickers)
        bench = fetch_prices_yf([opts["benchmark"]]).get(opts["benchmark"])
        if bench is None or bench.empty:
            self.stderr.write(f"Benchmark {opts['benchmark']} missing")
            return
        bench_close = bench["Close"].dropna()

        # 3) 準備關閉價字典
        closes = {t: df["Close"].dropna() for t, df in prices.items() if "Close" in df.columns and len(df) >= 200}

        # 4) RS 百分位
        rs_map = rs_percentile_universe(closes, bench_close)

        # 5) 取新聞 window_score（7日窗，你 rollup_signals 已寫入）
        sig_map = defaultdict(float)
        for row in AnalyticsCompanySignal.objects.filter(company_id__in=list(qs.values_list("id", flat=True))).values("company_id", "window_score"):
            sig_map[row["company_id"]] = float(row["window_score"] or 0.0)

        # 6) 遍歷計算 Stage2 + 終分
        rows = []
        id_by_symbol = {c.ticker: c.id for c in qs}
        for sym, df in prices.items():
            if sym not in rs_map:
                continue
            rs100 = rs_map[sym]["rs100"]
            if rs100 is None or math.isnan(rs100):
                continue

            # Stage2
            passed, reasons = minervini_stage2(
                df["Close"].dropna(), df["High"].dropna(), df["Low"].dropna(),
                rs100=rs100, rs_threshold=opts["rs_threshold"]
            )

            # 新聞權重（公司 id）
            cid = id_by_symbol.get(sym)
            wscore = sig_map.get(cid, 0.0)
            wfactor = news_weight_factor(wscore, alpha=opts["alpha"], k=opts["k"])  # 例：1 ± 0.2

            final = float(max(0.0, min(100.0, rs100 * wfactor)))

            rows.append({
                "company_id": cid,
                "ticker": sym,
                "rs100": float(rs100),
                "p1m": rs_map[sym]["p1m"],
                "p3m": rs_map[sym]["p3m"],
                "p6m": rs_map[sym]["p6m"],
                "stage2": passed,
                "reasons": reasons,
                "news_window_score": wscore,
                "news_weight_factor": wfactor,
                "final": final,
                "ma": {
                    "last_close": float(df["Close"].iloc[-1]),
                    "ma50": float(df["Close"].rolling(50).mean().iloc[-1]),
                    "ma150": float(df["Close"].rolling(150).mean().iloc[-1]),
                    "ma200": float(df["Close"].rolling(200).mean().iloc[-1]),
                }
            })

        if not rows:
            self.stderr.write("No computed rows.")
            return

        # 7) 排序（Stage2 優先，再按 final）
        rows.sort(key=lambda x: (not x["stage2"], -x["final"]))  # Stage2=True 先
        top = rows[: opts["save_top"]]

        # 8) 寫入 DB（覆蓋同日）
        from django.db import transaction
        with transaction.atomic():
            # 刪掉同日舊紀錄（避免 rank 錯）
            AnalyticsRecommendation.objects.filter(as_of_date=today).delete()

            for rnk, r in enumerate(top, start=1):
                AnalyticsRecommendation.objects.create(
                    company_id=r["company_id"],
                    as_of_date=today,
                    rs_score=Decimal(str(round(r["rs100"], 2))),
                    rs_p1m=Decimal(str(round(r["p1m"], 2))) if r["p1m"] is not None else None,
                    rs_p3m=Decimal(str(round(r["p3m"], 2))) if r["p3m"] is not None else None,
                    rs_p6m=Decimal(str(round(r["p6m"], 2))) if r["p6m"] is not None else None,
                    rs_method="percentile_relret_1/3/6m_wt=0.2/0.3/0.5",
                    stage2_pass=r["stage2"],
                    stage2_reasons=r["reasons"],
                    news_window_score=Decimal(str(round(r["news_window_score"], 6))),
                    news_weight_factor=Decimal(str(round(r["news_weight_factor"], 3))),
                    final_score=Decimal(str(round(r["final"], 3))),
                    rank=rnk,
                    details=r["ma"],
                )

        self.stdout.write(self.style.SUCCESS(f"Saved {len(top)} recommendations for {today}"))
        # 顯示頭 20 隻
        for r in top[:20]:
            tag = "★" if r["stage2"] else " "
            self.stdout.write(f"{tag} {r['ticker']:<6} final={r['final']:.1f}  RS={r['rs100']:.1f}  w={r['news_weight_factor']:.2f}")