import json, math
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from reference.models import Company
from research.models import (
    CompanyProfile, CompanyRevenueByProduct, CompanyRevenueByGeography,
    CompanyCustomerShare, CompanySupplierShare, CompanyRisk,
    CompanyCatalyst, CompanyCompetitor, CompanyRelatedStock, CompanyThesis,
)
from research.schemas import CompanyAIOutput
from research.llm_client import llm_json

# ---- 更強 Prompt ----
COMPANY_PROMPT_TEMPLATE = """\
你是一名嚴謹的賬面分析師。請根據 10-K/10-Q/8-K、IR年報/簡報、可信媒體，
以**JSON**輸出以下公司研究結果。**禁止**輸出 JSON 以外的任何文字。

[公司識別]
Ticker: {ticker}
Company Name: {name}
Industry: {industry_name}
Country: {country}

[輸出格式（JSON Schema 範例，必須包含所有字段；未知用 null/空陣列）]
{schema}

[規則]
- 語言：英文（保持技術名詞準確）
- 金額幣別：使用字段 currency（預設 {currency}），所有 *usd 欄位以該幣別（USD）表示
- 年份：as_of_year = {year}；如能提供季度，填寫 as_of_quarter ("Q1".."Q4")
- 百分比分配需盡量覆蓋主體收入（product/geography），條目數 3~8；如為估算，is_estimate=true
- 每個條目（product/geography/customer/supplier/risk/catalyst/competitor/related_stocks/thesis）
  儘量給出 evidence：source_url + 不多於3句 evidence_sentences + confidence_0_1
- 風險/催化包含 half_life_days（典型：earnings 5~7；規管/制裁 30~180）
- 競爭者包含 market_name（競爭細分，例如 "advanced foundry"）與 market_share_pct（如可）
- Related stocks 必須包含 relation_type（supplier/customer/peer/ETF/partner）
- **禁止幻覺**：如來源不明請把對應數值設為 null 或 is_estimate=true；必填 evidence.confidence_0_1<=0.5
- 僅輸出 JSON；不要加註解、不要 Markdown。
"""

def schema_example() -> str:
    # 僅作為 LLM 參考，不用作程式校驗（程式用 Pydantic）
    return json.dumps({
        "as_of_year": 2025,
        "as_of_quarter": "Q2",
        "currency": "USD",
        "business_model_summary": "string",
        "growth_drivers": "string",
        "revenue_by_product": [
            {"product":"Service A","revenue_pct":35.2,"revenue_usd":12000000000,"is_estimate":True,
             "evidence":{"source_url":"https://...","evidence_sentences":["..."],"confidence_0_1":0.7}}
        ],
        "revenue_by_geography": [
            {"region":"North America","revenue_pct":42.0,"revenue_usd":15000000000,"is_estimate":True,
             "evidence":{"source_url":"https://...","evidence_sentences":["..."],"confidence_0_1":0.6}}
        ],
        "largest_customers": [
            {"name":"Customer X","revenue_pct":18.0,"is_estimate":True,
             "evidence":{"source_url":"https://...","evidence_sentences":["..."],"confidence_0_1":0.6}}
        ],
        "largest_suppliers": [
            {"name":"Supplier Y","cost_pct":20.0,"is_estimate":True,
             "evidence":{"source_url":"https://...","evidence_sentences":["..."],"confidence_0_1":0.5}}
        ],
        "risks": [
            {"category":"Regulation","description":"...","horizon":"short","severity_1_5":3,"likelihood_1_5":3,"half_life_days":60,
             "evidence":{"source_url":"https://...","evidence_sentences":["..."],"confidence_0_1":0.7}}
        ],
        "catalysts": [
            {"description":"...","positive":True,"timeframe_months":6,"probability_0_1":0.6,"expected_impact":"...","half_life_days":20,
             "evidence":{"source_url":"https://...","evidence_sentences":["..."],"confidence_0_1":0.7}}
        ],
        "competitors": [
            {"name":"Samsung","ticker":"KRX:005930","market_share_pct":None,"market_name":"advanced memory",
             "evidence":{"source_url":"https://...","evidence_sentences":["..."],"confidence_0_1":0.6}}
        ],
        "related_stocks": [
            {"symbol":"ASML","name":"ASML Holding","relation_text":"...","relation_type":"supplier",
             "evidence":{"source_url":"https://...","evidence_sentences":["..."],"confidence_0_1":0.6}}
        ],
        "theses": [
            {"side":"for","content":"...","evidence":{"source_url":None,"evidence_sentences":["..."],"confidence_0_1":0.6}},
            {"side":"against","content":"...","evidence":{"source_url":None,"evidence_sentences":["..."],"confidence_0_1":0.6}}
        ]
    }, ensure_ascii=False)

def _normalize_pct(items, pct_key):
    """把多個 item 的百分比做簡單歸一化（總和近似 100）"""
    vals = [getattr(i, pct_key) for i in items if getattr(i, pct_key) is not None]
    s = sum(vals) if vals else 0
    if not vals or s == 0:
        return items
    factor = 100.0 / s
    for i in items:
        v = getattr(i, pct_key)
        if v is not None:
            nv = round(float(v) * factor, 2)
            setattr(i, pct_key, nv)
    return items

class Command(BaseCommand):
    help = "用 DeepSeek 生成（高細節版）公司的研究內容並寫入 research 表"

    def add_arguments(self, parser):
        parser.add_argument("--ticker", type=str, required=True)
        parser.add_argument("--industry", type=str, default="")
        parser.add_argument("--currency", type=str, default="USD")
        parser.add_argument("--replace", action="store_true")

    @transaction.atomic
    def handle(self, *args, **opts):
        ticker = opts["ticker"].strip().upper()
        industry_hint = opts["industry"].strip()
        currency = opts["currency"].strip().upper() or "USD"
        replace = opts["replace"]

        try:
            company = Company.objects.get(ticker=ticker)
        except Company.DoesNotExist:
            raise CommandError(f"Company not found: {ticker}")

        industry_name = industry_hint or (company.industry.name if company.industry else "")
        prompt = COMPANY_PROMPT_TEMPLATE.format(
            ticker=company.ticker, name=company.name,
            industry_name=industry_name, country=company.country,
            schema=schema_example(), currency=currency, year=timezone.now().year
        )

        raw = llm_json(prompt)
        data = CompanyAIOutput(**raw)  # Pydantic 驗證

        year = data.as_of_year

        # ---- 可選：把 product / geography 的百分比 normalize 到 ~100
        data.revenue_by_product = _normalize_pct(data.revenue_by_product, "revenue_pct")
        data.revenue_by_geography = _normalize_pct(data.revenue_by_geography, "revenue_pct")

        if replace:
            CompanyRevenueByProduct.objects.filter(company=company, year=year).delete()
            CompanyRevenueByGeography.objects.filter(company=company, year=year).delete()
            CompanyCustomerShare.objects.filter(company=company, year=year).delete()
            CompanySupplierShare.objects.filter(company=company, year=year).delete()
            CompanyRisk.objects.filter(company=company).delete()
            CompanyCatalyst.objects.filter(company=company).delete()
            CompanyCompetitor.objects.filter(company=company).delete()
            CompanyRelatedStock.objects.filter(company=company).delete()
            CompanyThesis.objects.filter(company=company).delete()

        # Profile
        prof, _ = CompanyProfile.objects.get_or_create(company=company)
        prof.business_model_summary = data.business_model_summary or ""
        prof.growth_drivers = data.growth_drivers or ""
        prof.save()

        # Revenue by product
        for rp in data.revenue_by_product:
            CompanyRevenueByProduct.objects.update_or_create(
                company=company, year=year, product=rp.product,
                defaults=dict(
                    revenue_pct=rp.revenue_pct, revenue_usd=rp.revenue_usd,
                    source_url=(rp.evidence.source_url if rp.evidence else "") or ""
                )
            )

        # Revenue by geography
        for rg in data.revenue_by_geography:
            CompanyRevenueByGeography.objects.update_or_create(
                company=company, year=year, region=rg.region,
                defaults=dict(
                    revenue_pct=rg.revenue_pct, revenue_usd=rg.revenue_usd,
                    source_url=(rg.evidence.source_url if rg.evidence else "") or ""
                )
            )

        # Customers
        for c in data.largest_customers:
            CompanyCustomerShare.objects.update_or_create(
                company=company, year=year, customer_name=c.name,
                defaults=dict(
                    revenue_pct=c.revenue_pct, is_estimate=c.is_estimate,
                    source_url=(c.evidence.source_url if c.evidence else "") or ""
                )
            )

        # Suppliers
        for s in data.largest_suppliers:
            CompanySupplierShare.objects.update_or_create(
                company=company, year=year, supplier_name=s.name,
                defaults=dict(
                    cost_pct=s.cost_pct, is_estimate=s.is_estimate,
                    source_url=(s.evidence.source_url if s.evidence else "") or ""
                )
            )

        # Risks
        for r in data.risks:
            CompanyRisk.objects.create(
                company=company, category=r.category, description=r.description,
                horizon=r.horizon, severity_1_5=r.severity_1_5, likelihood_1_5=r.likelihood_1_5,
                source_url=(r.evidence.source_url if r.evidence else "") or "",
                as_of=None
            )

        # Catalysts
        for c in data.catalysts:
            CompanyCatalyst.objects.create(
                company=company, description=c.description, positive=c.positive,
                timeframe_months=c.timeframe_months, probability_0_1=c.probability_0_1,
                expected_impact=c.expected_impact or "",
                source_url=(c.evidence.source_url if c.evidence else "") or "",
                as_of=None
            )

        # Competitors
        for comp in data.competitors:
            competitor_obj = None
            if comp.ticker:
                competitor_obj = Company.objects.filter(ticker=comp.ticker.upper()).first()
            CompanyCompetitor.objects.create(
                company=company, competitor=competitor_obj,
                competitor_name=comp.name, competitor_ticker=(comp.ticker or ""),
                market_share_pct=comp.market_share_pct, market_name=comp.market_name or ""
            )

        # Related stocks
        for rel in data.related_stocks:
            CompanyRelatedStock.objects.update_or_create(
                company=company, symbol=rel.symbol.upper(),
                defaults=dict(
                    name=rel.name or "",
                    relation_text=rel.relation_text,
                    relation_type=rel.relation_type or ""
                )
            )

        # Theses
        for th in data.theses:
            CompanyThesis.objects.create(company=company, side=th.side, content=th.content)

        self.stdout.write(self.style.SUCCESS(
            f"[OK] Saved detailed research for {company.ticker} ({year}, currency={data.currency})."
        ))