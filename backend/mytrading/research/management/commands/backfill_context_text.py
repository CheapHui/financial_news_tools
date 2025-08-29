from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from reference.models import Company
from research.models import (
    CompanyProfile, CompanyRisk, CompanyCatalyst, CompanyThesis,
    CompanyRelatedStock, IndustryProfile, IndustryPlayer,
)

def enrich_catalyst(c: CompanyCatalyst) -> str:
    when = c.as_of.isoformat() if c.as_of else timezone.now().date().isoformat()
    pos = "positive" if c.positive else "negative"
    tf = f"in {c.timeframe_months} months" if c.timeframe_months else "in the next year"
    prob = f" (prob {c.probability_0_1:.2f})" if c.probability_0_1 is not None else ""
    impact = f" Expected impact: {c.expected_impact}." if c.expected_impact else ""
    return (f"As of {when}, {c.company.ticker} catalyst ({pos}): {c.description}. "
            f"Timeframe {tf}{prob}.{impact}")

def enrich_risk(r: CompanyRisk) -> str:
    when = r.as_of.isoformat() if r.as_of else timezone.now().date().isoformat()
    return (f"As of {when}, {r.company.ticker} risk [{r.category}] "
            f"(horizon {r.horizon}, severity {r.severity_1_5}/5, likelihood {r.likelihood_1_5}/5): "
            f"{r.description}")

def enrich_thesis(t: CompanyThesis) -> str:
    side = "Bull case" if t.side == "for" else "Bear case"
    return f"{t.company.ticker} {side}: {t.content}"

def enrich_profile(p: CompanyProfile) -> str:
    parts = []
    if p.business_model_summary: parts.append(p.business_model_summary)
    if p.growth_drivers: parts.append(f"Growth drivers: {p.growth_drivers}")
    return " ".join(parts)

def enrich_related(rs: CompanyRelatedStock) -> str:
    name = f"{rs.name} " if rs.name else ""
    rtype = f" ({rs.relation_type})" if rs.relation_type else ""
    return f"{rs.company.ticker} related: {name}{rs.symbol}{rtype}. {rs.relation_text}"

def enrich_industry_profile(ip: IndustryProfile) -> str:
    parts = []
    if ip.overview_under_1000w: parts.append(ip.overview_under_1000w)
    if ip.value_chain_summary: parts.append(f"Value chain: {ip.value_chain_summary}")
    if ip.trends: parts.append(f"Trends: {ip.trends}")
    if ip.catalysts: parts.append(f"Catalysts: {ip.catalysts}")
    return " ".join(parts)

def enrich_industry_player(pl: IndustryPlayer) -> str:
    head = pl.company.ticker if pl.company else (pl.symbol or pl.name)
    tail = f" Role={pl.role}. {pl.summary_under_300w or ''}".strip()
    growth = []
    if pl.revenue_growth_5y_pct is not None: growth.append(f"Rev5Y {pl.revenue_growth_5y_pct}%")
    if pl.profit_growth_5y_pct is not None: growth.append(f"Profit5Y {pl.profit_growth_5y_pct}%")
    g = ("; ".join(growth)) if growth else ""
    return f"{head}: {tail} {g}".strip()

MAPS = [
    (CompanyProfile, "context_text", enrich_profile),
    (CompanyRisk, "context_text", enrich_risk),
    (CompanyCatalyst, "context_text", enrich_catalyst),
    (CompanyThesis, "context_text", enrich_thesis),
    (CompanyRelatedStock, "context_text", enrich_related),
    (IndustryProfile, "context_text", enrich_industry_profile),
    (IndustryPlayer, "context_text", enrich_industry_player),
]

class Command(BaseCommand):
    help = "Backfill context_text for all embeddable models with richer paragraph-style text."

    def add_arguments(self, parser):
        parser.add_argument("--overwrite", action="store_true", help="Overwrite non-empty context_text")

    @transaction.atomic
    def handle(self, *args, **opts):
        overwrite = opts["overwrite"]
        total = 0
        for Model, field, fn in MAPS:
            qs = Model.objects.all()
            for obj in qs:
                cur = (getattr(obj, field) or "").strip()
                if cur and not overwrite:
                    continue
                text = fn(obj).strip()
                if not text:
                    continue
                setattr(obj, field, text)
                obj.save(update_fields=[field])
                total += 1
        self.stdout.write(self.style.SUCCESS(f"Backfilled {total} records."))