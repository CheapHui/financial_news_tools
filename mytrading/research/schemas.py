from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal

# ---------- Common ----------
class Evidence(BaseModel):
    source_url: Optional[str] = None
    evidence_sentences: List[str] = []  # 原文關鍵句（<=3句）
    confidence_0_1: float = Field(0.5, ge=0, le=1)

# ---------- Company ----------
class RevenueProduct(BaseModel):
    product: str
    revenue_pct: Optional[float] = Field(None, ge=0, le=100)
    revenue_usd: Optional[float] = None  # 以 currency 註明
    is_estimate: bool = False
    evidence: Optional[Evidence] = None

class RevenueGeography(BaseModel):
    region: str
    revenue_pct: Optional[float] = Field(None, ge=0, le=100)
    revenue_usd: Optional[float] = None
    is_estimate: bool = False
    evidence: Optional[Evidence] = None

class CustomerShare(BaseModel):
    name: str
    revenue_pct: Optional[float] = Field(None, ge=0, le=100)
    is_estimate: bool = False
    evidence: Optional[Evidence] = None

class SupplierShare(BaseModel):
    name: str
    cost_pct: Optional[float] = Field(None, ge=0, le=100)
    is_estimate: bool = False
    evidence: Optional[Evidence] = None

class RiskItem(BaseModel):
    category: str  # Regulation/Supply/Competition/FX/Macro/Execution/Cyber/Legal/ESG
    description: str
    horizon: Literal["short","medium","long"] = "short"
    severity_1_5: int = Field(3, ge=1, le=5)
    likelihood_1_5: int = Field(3, ge=1, le=5)
    half_life_days: Optional[int] = Field(30, ge=1, le=720)
    evidence: Optional[Evidence] = None

class CatalystItem(BaseModel):
    description: str
    positive: bool = True
    timeframe_months: Optional[int] = None
    probability_0_1: Optional[float] = Field(None, ge=0, le=1)
    expected_impact: Optional[str] = None
    half_life_days: Optional[int] = Field(30, ge=1, le=720)
    evidence: Optional[Evidence] = None

class CompetitorItem(BaseModel):
    name: str
    ticker: Optional[str] = None
    market_share_pct: Optional[float] = Field(None, ge=0, le=100)
    market_name: Optional[str] = None
    evidence: Optional[Evidence] = None

class RelatedStockItem(BaseModel):
    symbol: str
    name: Optional[str] = None
    relation_text: str  # 兩句描述
    relation_type: Optional[str] = None  # supplier/customer/peer/ETF/partner
    evidence: Optional[Evidence] = None

class ThesisItem(BaseModel):
    side: Literal["for","against"]
    content: str
    evidence: Optional[Evidence] = None

class CompanyAIOutput(BaseModel):
    as_of_year: int
    as_of_quarter: Optional[str] = None  # e.g. "Q2"
    currency: str = "USD"

    business_model_summary: str
    growth_drivers: Optional[str] = None

    revenue_by_product: List[RevenueProduct] = []
    revenue_by_geography: List[RevenueGeography] = []
    largest_customers: List[CustomerShare] = []
    largest_suppliers: List[SupplierShare] = []

    risks: List[RiskItem] = []
    catalysts: List[CatalystItem] = []
    competitors: List[CompetitorItem] = []
    related_stocks: List[RelatedStockItem] = []
    theses: List[ThesisItem] = []

    @validator("revenue_by_product", "revenue_by_geography")
    def clamp_pct_list(cls, items):
        # 允許空；數值範圍已由字段保障
        return items

# ---------- Industry ----------
class IndustryPlayerItem(BaseModel):
    name: str
    role: Optional[str] = "producer"   # supplier/producer/distributor/retailer/platform/other
    summary_under_300w: Optional[str] = None
    largest_customers: List[CustomerShare] = []
    largest_suppliers: List[SupplierShare] = []
    symbol: Optional[str] = None
    market_cap_usd: Optional[float] = None
    revenue_growth_5y_pct: Optional[float] = None
    profit_growth_5y_pct: Optional[float] = None
    evidence: Optional[Evidence] = None

class IndustryAIOutput(BaseModel):
    overview_under_1000w: str
    trends: Optional[str] = None
    catalysts: Optional[str] = None
    value_chain_summary: Optional[str] = None
    players: List[IndustryPlayerItem] = []