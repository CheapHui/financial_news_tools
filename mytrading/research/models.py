from django.db import models
from django.utils import timezone
from reference.models import Company, Industry


# --------- 共用基類 ---------
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True


class PctField(models.DecimalField):
    """百分比 0-100"""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_digits", 6)
        kwargs.setdefault("decimal_places", 3)
        super().__init__(*args, **kwargs)


# --------- 公司層 ---------
class CompanyProfile(TimeStampedModel):
    """
    長文描述（商業模式／成長動能／營運重點等）
    向量請寫入通用 embeddings 表（object_type='company_profile'）
    """
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name="profile")
    business_model_summary = models.TextField(blank=True, default="")
    growth_drivers = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")

    def to_card_text(self) -> str:
        parts = []
        if self.business_model_summary:
            parts.append(f"Business model: {self.business_model_summary}")
        if self.growth_drivers:
            parts.append(f"Growth drivers: {self.growth_drivers}")
        if self.notes:
            parts.append(f"Notes: {self.notes}")
        return "\n".join(parts).strip()


class CompanyRevenueByProduct(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="rev_products")
    year = models.IntegerField()
    product = models.CharField(max_length=160)
    revenue_usd = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    revenue_pct = PctField(null=True, blank=True)  # 0..100
    source_url = models.URLField(blank=True, default="")

    class Meta:
        unique_together = [("company", "year", "product")]
        indexes = [models.Index(fields=["company", "year"])]

    def to_card_text(self) -> str:
        pct = f"{self.revenue_pct}%" if self.revenue_pct is not None else "N/A"
        usd = f"${self.revenue_usd:,}" if self.revenue_usd is not None else "N/A"
        return (f"{self.company.ticker} {self.year} product mix: {self.product} "
                f"revenue {usd}, {pct} of total.")


class CompanyRevenueByGeography(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="rev_geos")
    year = models.IntegerField()
    region = models.CharField(max_length=120)  # e.g. North America, EMEA, China
    revenue_usd = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    revenue_pct = PctField(null=True, blank=True)
    source_url = models.URLField(blank=True, default="")

    class Meta:
        unique_together = [("company", "year", "region")]
        indexes = [models.Index(fields=["company", "year"])]

    def to_card_text(self) -> str:
        pct = f"{self.revenue_pct}%" if self.revenue_pct is not None else "N/A"
        usd = f"${self.revenue_usd:,}" if self.revenue_usd is not None else "N/A"
        return (f"{self.company.ticker} {self.year} geographic mix: {self.region} "
                f"revenue {usd}, {pct} of total.")


class CompanyCustomerShare(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="customers")
    year = models.IntegerField()
    customer_name = models.CharField(max_length=200)
    revenue_pct = PctField(null=True, blank=True)
    is_estimate = models.BooleanField(default=False)
    source_url = models.URLField(blank=True, default="")

    class Meta:
        unique_together = [("company", "year", "customer_name")]
        indexes = [models.Index(fields=["company", "year"])]

    def to_card_text(self) -> str:
        est = " (estimate)" if self.is_estimate else ""
        pct = f"{self.revenue_pct}%" if self.revenue_pct is not None else "N/A"
        return (f"{self.company.ticker} {self.year} largest customer: {self.customer_name}{est}, "
                f"{pct} of revenue.")


class CompanySupplierShare(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="suppliers")
    year = models.IntegerField()
    supplier_name = models.CharField(max_length=200)
    cost_pct = PctField(null=True, blank=True)  # 佔成本百分比
    is_estimate = models.BooleanField(default=False)
    source_url = models.URLField(blank=True, default="")

    class Meta:
        unique_together = [("company", "year", "supplier_name")]
        indexes = [models.Index(fields=["company", "year"])]

    def to_card_text(self) -> str:
        est = " (estimate)" if self.is_estimate else ""
        pct = f"{self.cost_pct}%" if self.cost_pct is not None else "N/A"
        return (f"{self.company.ticker} {self.year} key supplier: {self.supplier_name}{est}, "
                f"{pct} of cost.")


class CompanyRisk(TimeStampedModel):
    RISK_HORIZON = [("short", "0-12m"), ("medium", "12-36m"), ("long", "36m+")]
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="risks")
    category = models.CharField(max_length=80)  # e.g. Regulation, Supply, Competition, FX
    description = models.TextField()
    horizon = models.CharField(max_length=10, choices=RISK_HORIZON, default="short")
    severity_1_5 = models.IntegerField(default=3)
    likelihood_1_5 = models.IntegerField(default=3)
    source_url = models.URLField(blank=True, default="")
    as_of = models.DateField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["company", "category"])]

    def to_card_text(self) -> str:
        when = self.as_of.isoformat() if self.as_of else timezone.now().date().isoformat()
        return (f"Risk ({self.company.ticker}) [{self.category}] as of {when}: "
                f"horizon={self.horizon}, severity={self.severity_1_5}/5, "
                f"likelihood={self.likelihood_1_5}/5. {self.description}")


class CompanyCatalyst(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="catalysts")
    description = models.TextField()
    positive = models.BooleanField(default=True)
    timeframe_months = models.IntegerField(null=True, blank=True)
    probability_0_1 = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)  # 0.00..1.00
    expected_impact = models.TextField(blank=True, default="")
    source_url = models.URLField(blank=True, default="")
    as_of = models.DateField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["company", "positive"])]

    def to_card_text(self) -> str:
        pos = "Positive" if self.positive else "Negative"
        prob = f"prob={self.probability_0_1}" if self.probability_0_1 is not None else "prob=N/A"
        tf = f"{self.timeframe_months}m" if self.timeframe_months else "N/A"
        return (f"Catalyst ({self.company.ticker}) [{pos}] timeframe={tf}, {prob}. "
                f"{self.description} {('Impact: ' + self.expected_impact) if self.expected_impact else ''}".strip())


class CompanyCompetitor(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="competitors_of")
    competitor = models.ForeignKey(
        Company, on_delete=models.SET_NULL, null=True, blank=True, related_name="competitor_targets"
    )
    competitor_name = models.CharField(max_length=200, blank=True, default="")
    competitor_ticker = models.CharField(max_length=20, blank=True, default="")
    market_share_pct = PctField(null=True, blank=True)
    market_name = models.CharField(max_length=120, blank=True, default="")  # 競爭的細分市場

    class Meta:
        indexes = [models.Index(fields=["company"])]

    def display_name(self) -> str:
        if self.competitor:
            return f"{self.competitor.ticker} - {self.competitor.name}"
        if self.competitor_ticker:
            return f"{self.competitor_ticker} - {self.competitor_name}"
        return self.competitor_name or "Unknown"

    def to_card_text(self) -> str:
        share = f"{self.market_share_pct}%" if self.market_share_pct is not None else "N/A"
        name = self.display_name()
        seg = f"segment={self.market_name}" if self.market_name else ""
        return f"{self.company.ticker} competitor: {name}, share {share}. {seg}".strip()


class CompanyRelatedStock(TimeStampedModel):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="related_stocks")
    symbol = models.CharField(max_length=20)
    name = models.CharField(max_length=200, blank=True, default="")
    relation_text = models.TextField()  # 兩句描述
    relation_type = models.CharField(max_length=80, blank=True, default="")  # e.g. supplier, customer, peer, ETF

    class Meta:
        unique_together = [("company", "symbol")]
        indexes = [models.Index(fields=["company"])]

    def to_card_text(self) -> str:
        nm = f"{self.name} " if self.name else ""
        rtype = f" ({self.relation_type})" if self.relation_type else ""
        return f"Related to {self.company.ticker}: {nm}{self.symbol}{rtype}. {self.relation_text}"


class CompanyThesis(TimeStampedModel):
    SIDE = [("for", "Bull"), ("against", "Bear")]
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="theses")
    side = models.CharField(max_length=8, choices=SIDE)
    content = models.TextField()

    class Meta:
        indexes = [models.Index(fields=["company", "side"])]

    def to_card_text(self) -> str:
        label = "Bull case" if self.side == "for" else "Bear case"
        return f"{self.company.ticker} {label}: {self.content}"


# --------- 行業層 ---------
class IndustryProfile(TimeStampedModel):
    """
    行業概覽／趨勢／催化／價值鏈摘要
    向量請寫入通用 embeddings 表（object_type='industry_profile'）
    """
    industry = models.OneToOneField(Industry, on_delete=models.CASCADE, related_name="profile")
    overview_under_1000w = models.TextField(blank=True, default="")
    trends = models.TextField(blank=True, default="")
    catalysts = models.TextField(blank=True, default="")
    value_chain_summary = models.TextField(blank=True, default="")

    def to_card_text(self) -> str:
        parts = []
        if self.overview_under_1000w:
            parts.append(f"Overview: {self.overview_under_1000w}")
        if self.trends:
            parts.append(f"Trends: {self.trends}")
        if self.catalysts:
            parts.append(f"Catalysts: {self.catalysts}")
        if self.value_chain_summary:
            parts.append(f"Value chain: {self.value_chain_summary}")
        return "\n".join(parts).strip()


class IndustryPlayer(TimeStampedModel):
    ROLE = [
        ("supplier","Supplier"), ("producer","Producer"), ("distributor","Distributor"),
        ("retailer","Retailer"), ("platform","Platform"), ("other","Other"), ("investor","Investor"), ("analyst","Analyst"), ("media","Media"), ("government","Government")
    ]
    industry = models.ForeignKey(Industry, on_delete=models.CASCADE, related_name="players")
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name="industry_roles")
    name = models.CharField(max_length=200)  # 如無公司主檔，用 name 填
    role = models.CharField(max_length=20, choices=ROLE, default="producer")
    summary_under_300w = models.TextField(blank=True, default="")
    largest_customers_json = models.JSONField(default=list, help_text='[{"name":"X","revenue_pct":30}]')
    largest_suppliers_json = models.JSONField(default=list, help_text='[{"name":"Y","cost_pct":20}]')
    revenue_growth_5y_pct = PctField(null=True, blank=True)
    profit_growth_5y_pct = PctField(null=True, blank=True)
    symbol = models.CharField(max_length=20, blank=True, default="")
    market_cap_usd = models.BigIntegerField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["industry","role"])]

    def to_card_text(self) -> str:
        comp = self.company.ticker if self.company else (self.symbol or self.name)
        rg = f"Rev 5Y {self.revenue_growth_5y_pct}%" if self.revenue_growth_5y_pct is not None else ""
        pg = f"Profit 5Y {self.profit_growth_5y_pct}%" if self.profit_growth_5y_pct is not None else ""
        lines = [
            f"{self.industry.name} player [{self.role}]: {comp}",
            self.summary_under_300w or "",
            rg, pg
        ]
        return " ".join([x for x in lines if x]).strip()