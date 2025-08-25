# research/management/commands/gen_industry_ai.py
import json
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from reference.models import Industry, Company
from research.models import IndustryProfile, IndustryPlayer
from research.schemas import IndustryAIOutput
from research.llm_client import llm_json

PROMPT = """\
You are an equity research analyst. Produce a **pure JSON** response only.
Use credible sources (10-K/20-F, investor presentations, regulator sites, reputable media).
If unknown, set null or mark low confidence in evidence.

[Industry]
Name: {industry_name}
Sector: {sector_name}

[JSON Schema example to follow exactly (all keys must appear)]
{schema}

[Rules]
- Language: English.
- Overview (<=1000 words) explains how the industry works: key activities, revenue pools, cost drivers, typical margins, cyclicality.
- Value chain summary: upstream→midstream→downstream mapping.
- Trends: list concrete demand/supply/technology/regulatory/capex cycles.
- Catalysts (12–24 months): specify regulatory, macro, product cycles, subsidies, capacity ramps; include dates/quarters if known.
- Players: up to 20 across value chain; fill role (supplier/producer/distributor/retailer/platform/other).
  Include summary_under_300w, largest_customers (name + revenue_pct if known), largest_suppliers (name + cost_pct if known),
  stock symbol (if public), USD market cap (if known), 5-year revenue/profit growth (percent if known).
- Every player and any % claims should include evidence with source_url, up to 3 evidence_sentences, confidence_0_1 in [0,1].
- NO extra text outside JSON. NO markdown.
"""

def schema_example() -> str:
    # 給 LLM 參考的 schema（實際驗證靠 Pydantic: IndustryAIOutput）
    return json.dumps({
        "overview_under_1000w": "string",
        "trends": "string",
        "catalysts": "string",
        "value_chain_summary": "string",
        "players": [
            {
                "name": "Example Co",
                "role": "supplier",
                "summary_under_300w": "Brief business summary...",
                "largest_customers": [
                    {
                        "name": "Customer A",
                        "revenue_pct": 25.0,
                        "is_estimate": True,
                        "evidence": {
                            "source_url": "https://...",
                            "evidence_sentences": ["..."],
                            "confidence_0_1": 0.6
                        }
                    }
                ],
                "largest_suppliers": [
                    {
                        "name": "Supplier B",
                        "cost_pct": None,
                        "is_estimate": True,
                        "evidence": {
                            "source_url": "https://...",
                            "evidence_sentences": ["..."],
                            "confidence_0_1": 0.5
                        }
                    }
                ],
                "symbol": "EXMPL",
                "market_cap_usd": 12300000045,
                "revenue_growth_5y_pct": 80.0,
                "profit_growth_5y_pct": 120.0,
                "evidence": {
                    "source_url": "https://...",
                    "evidence_sentences": ["..."],
                    "confidence_0_1": 0.7
                }
            }
        ]
    }, ensure_ascii=False)

class Command(BaseCommand):
    help = "Generate a detailed industry report via DeepSeek and persist to IndustryProfile/IndustryPlayer."

    def add_arguments(self, parser):
        parser.add_argument("--industry-id", type=int, required=True, help="reference.Industry pk")
        parser.add_argument("--replace", action="store_true", help="Delete existing profile/players before insert")

    @transaction.atomic
    def handle(self, *args, **opts):
        ind_id = opts["industry_id"]
        replace = opts["replace"]

        try:
            industry = Industry.objects.get(id=ind_id)
        except Industry.DoesNotExist:
            raise CommandError(f"Industry not found: id={ind_id}")

        prompt = PROMPT.format(
            industry_name=industry.name,
            sector_name=industry.sector.name if industry.sector else "",
            schema=schema_example(),
        )

        # --- LLM call & validation
        raw = llm_json(prompt)
        data = IndustryAIOutput(**raw)  # pydantic validation

        # --- Replace existing (optional)
        if replace:
            IndustryPlayer.objects.filter(industry=industry).delete()
            IndustryProfile.objects.filter(industry=industry).delete()

        # --- Upsert profile
        prof, _ = IndustryProfile.objects.get_or_create(industry=industry)
        prof.overview_under_1000w = data.overview_under_1000w or ""
        prof.trends = data.trends or ""
        prof.catalysts = data.catalysts or ""
        prof.value_chain_summary = data.value_chain_summary or ""
        prof.save()

        # --- Upsert players
        for p in data.players:
            # 嘗試 map 到已存在的 Company（靠 ticker）
            comp = None
            if p.symbol:
                comp = Company.objects.filter(ticker=p.symbol.upper()).first()

            IndustryPlayer.objects.create(
                industry=industry,
                company=comp,
                name=p.name,
                role=p.role or "producer",
                summary_under_300w=p.summary_under_300w or "",
                # 直接把 evidence 一齊寫入 JSON 欄位，方便往後檢索/審計
                largest_customers_json=[c.dict() for c in p.largest_customers],
                largest_suppliers_json=[s.dict() for s in p.largest_suppliers],
                symbol=(p.symbol or ""),
                market_cap_usd=p.market_cap_usd,
                revenue_growth_5y_pct=p.revenue_growth_5y_pct,
                profit_growth_5y_pct=p.profit_growth_5y_pct,
            )

        self.stdout.write(self.style.SUCCESS(f"[OK] Saved detailed industry research for '{industry.name}'."))