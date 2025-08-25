from django.db import models
from reference.models import Company

class PeriodType(models.TextChoices):
    ANNUAL = "annual", "Annual"
    QUARTER = "quarter", "Quarterly"

# 你需要嘅常見指標（可再擴）
FIN_METRICS = [
    # Income Statement
    "revenue", "gross_profit", "operating_income", "net_income",
    "eps_basic", "eps_diluted",
    # Balance Sheet
    "total_assets", "total_liabilities", "total_equity",
    "current_assets", "current_liabilities", "cash_and_equivalents", "inventories", "receivables",
    # Cash Flow
    "cash_from_operations", "capex", "free_cash_flow",
    # Others
    "interest_expense", "shares_diluted", "dividends_paid",
]

class FinancialFact(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="facts")
    period_type = models.CharField(max_length=10, choices=PeriodType.choices)
    period_end_date = models.DateField()  # e.g. 2024-12-31
    fiscal_year = models.IntegerField()
    fiscal_quarter = models.IntegerField(null=True, blank=True)  # 1..4 for quarter
    metric = models.CharField(max_length=64)   # must be in FIN_METRICS by convention
    value = models.DecimalField(max_digits=24, decimal_places=6, null=True)  # USD or units (document in ETL)
    source = models.CharField(max_length=40, default="reported")  # reported / computed / estimate
    as_reported_currency = models.CharField(max_length=8, default="USD")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["company", "metric"]),
            models.Index(fields=["company", "period_type", "period_end_date"]),
        ]
        unique_together = [("company", "period_type", "period_end_date", "metric")]