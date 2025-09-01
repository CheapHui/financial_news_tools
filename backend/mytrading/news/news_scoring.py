import os
import json
import time
import math
import re
from typing import List, Optional, Dict, Any, Literal
import requests
from pydantic import BaseModel, Field, HttpUrl, ValidationError, field_validator
from datetime import datetime, timezone, timedelta

# =========================
# Pydantic schema（news_scores）
# =========================

class SentimentTarget(BaseModel):
    target: str                                 # e.g. ticker / company / industry
    score: float = Field(ge=-1.0, le=1.0)       # -1 ~ 1
    confidence: float = Field(ge=0, le=1)

class EventFact(BaseModel):
    type: str                                   # e.g. "M&A", "Guidance", "Regulatory", "Product", "Macro"
    headline: str
    actors: List[str] = []
    action: str
    objects: List[str] = []
    time_ref: Optional[str] = None              # e.g. "2025-08-30", "Q3", "today"
    location: Optional[str] = None
    magnitude: Optional[str] = None             # e.g. "+12% YoY", "$2.3B", "Class Action Filed"

class CredibilitySignal(BaseModel):
    source_reputation: Literal["low","medium","high"]
    cross_ref_count: int = Field(ge=0)
    has_primary_source: bool

class ScoreBlock(BaseModel):
    impact_score: float = Field(ge=0, le=1)
    sentiment_score: float = Field(ge=-1, le=1)
    novelty_score: float = Field(ge=0, le=1)
    credibility_score: float = Field(ge=0, le=1)
    decay_half_life_hours: int = Field(ge=1)    # news half-life parameter used by你之前的rollup
    decayed_weight: float = Field(ge=0, le=1)   # exp(-age / half_life)

class NewsScores(BaseModel):
    item_id: str
    source_url: Optional[HttpUrl] = None
    published_at: Optional[datetime] = None
    tickers: List[str] = []
    industries: List[str] = []

    language: Optional[str] = None
    summary: Optional[str] = None

    events: List[EventFact] = []
    sentiment_overall: float = Field(ge=-1, le=1)
    targets: List[SentimentTarget] = []
    credibility: CredibilitySignal

    scores: ScoreBlock

    raw_model: Dict[str, Any] = Field(default_factory=dict)  # 可存 R1 trace / thoughts（去敏後）
    model_name: str
    model_latency_ms: int

    @field_validator("published_at", mode="before")
    @classmethod
    def _parse_dt(cls, v):
        if v is None or isinstance(v, datetime):
            return v
        # 允許 ISO 字串
        try:
            return datetime.fromisoformat(str(v).replace("Z","+00:00"))
        except Exception:
            return None


# =========================
# DeepSeek Client（OpenAI-compatible）
# =========================

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE = os.getenv("DEEPSEEK_BASE", "https://api.deepseek.com")
# Chat completions endpoint（OpenAI-style）
DEEPSEEK_CHAT_PATH = os.getenv("DEEPSEEK_CHAT_PATH", "/chat/completions")

class DeepSeekClient:
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or DEEPSEEK_API_KEY
        self.base_url = (base_url or DEEPSEEK_BASE).rstrip("/")
        if not self.api_key:
            raise RuntimeError("Missing DEEPSEEK_API_KEY")

    def chat(self, *, model: str, messages: List[Dict[str, str]], temperature: float = 0.2, response_format: Optional[Dict]=None) -> Dict[str, Any]:
        """
        兼容 deepseek-chat / deepseek-reasoner。
        """
        url = f"{self.base_url}{DEEPSEEK_CHAT_PATH}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format:
            # 部分供應商支援 { "type": "json_object" }
            payload["response_format"] = response_format

        t0 = time.time()
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        latency_ms = int((time.time() - t0) * 1000)

        if resp.status_code != 200:
            raise RuntimeError(f"DeepSeek error {resp.status_code}: {resp.text}")

        data = resp.json()
        # OpenAI style
        content = data["choices"][0]["message"].get("content", "")
        # R1（reasoner）會有 reasoning_content，可保存在 raw_model
        reasoning_content = data["choices"][0]["message"].get("reasoning_content")
        return {
            "content": content,
            "raw": data,
            "latency_ms": latency_ms,
            "reasoning_content": reasoning_content,
            "model": model,
        }


# =========================
# Prompt 模版（事件抽取 + 情緒）
# =========================

SYSTEM_PROMPT = """你是一個金融新聞抽取器。
任務：從輸入新聞文本抽取【可交易事件】與【情緒】，並嚴格輸出 JSON（不可包含多餘文字）。
事件需對股票價格或風險溢價有潛在影響（如：盈利指引、監管行動、重大合約、產品發佈、供應鏈事故、訴訟、M&A、裁員、股本變動、宏觀數據等）。
情緒分數在 -1 到 1，信心 0 到 1。
Novelty 以是否為新資訊衡量；Credibility 以來源權威 / 是否有一手資料 / 交叉引用衡量。
所有欄位必填或用合理預設。
只輸出 JSON。"""

USER_PROMPT_TEMPLATE = """請分析以下新聞內容，並輸出符合 schema 的 JSON。

Metadata:
- item_id: {item_id}
- source_url: {source_url}
- published_at: {published_at}
- tickers: {tickers}
- industries: {industries}
- decay_half_life_hours: {half_life_hours}

文本（可能包含多段）：
輸出 JSON Schema（鍵名不可更改）：
{{
  "item_id": "string",
  "source_url": "string|null",
  "published_at": "ISO8601|null",
  "tickers": ["..."],
  "industries": ["..."],
  "language": "string|null",
  "summary": "string|null",
  "events": [
    {{
      "type": "string",
      "headline": "string",
      "actors": ["..."],
      "action": "string",
      "objects": ["..."],
      "time_ref": "string|null",
      "location": "string|null",
      "magnitude": "string|null"
    }}
  ],
  "sentiment_overall": -1.0,
  "targets": [
    {{ "target": "string", "score": -1.0, "confidence": 0.0 }}
  ],
  "credibility": {{
    "source_reputation": "low|medium|high",
    "cross_ref_count": 0,
    "has_primary_source": true
  }},
  "scores": {{
    "impact_score": 0.0,
    "sentiment_score": -1.0,
    "novelty_score": 0.0,
    "credibility_score": 0.0,
    "decay_half_life_hours": {half_life_hours},
    "decayed_weight": 0.0
  }},
  "raw_model": {{ "note": "可放 reasoning 簡述，不得洩漏個資" }},
  "model_name": "string",
  "model_latency_ms": 0
}}
注意：
1) `scores.decayed_weight = exp(-max(0, age_hours) / decay_half_life_hours)`，age_hours = 現在 - published_at（小數）
2) 若無 published_at，decayed_weight = 1.0
3) 保持 JSON 可被嚴格解析；不要放 Markdown code fence
"""


# =========================
# JSON 安全處理
# =========================

JSON_BLOCK_RE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)

def coerce_json(text: str) -> str:
    """
    模型有機會回返 ```json ... ```；剝走圍欄。
    """
    m = JSON_BLOCK_RE.match(text.strip())
    if m:
        return m.group(1).strip()
    return text.strip()


# =========================
# 主流程：事件 + 情緒 → 驗證 → 填補 → 回傳
# =========================

def extract_news_scores(
    *,
    item_id: str,
    body: str,
    source_url: Optional[str] = None,
    published_at: Optional[datetime] = None,
    tickers: Optional[List[str]] = None,
    industries: Optional[List[str]] = None,
    model: str = "deepseek-reasoner",          # 可改 "deepseek-chat"
    temperature: float = 0.2,
    half_life_hours: int = 72,
    client: Optional[DeepSeekClient] = None,
    retries: int = 2,
) -> NewsScores:
    """
    呼叫 DeepSeek，抽取事件與情緒，經 Pydantic 驗證後回傳 NewsScores。
    """
    client = client or DeepSeekClient()

    user_prompt = USER_PROMPT_TEMPLATE.format(
        item_id=item_id,
        source_url=source_url or "null",
        published_at=(published_at.isoformat() if published_at else "null"),
        tickers=json.dumps(tickers or []),
        industries=json.dumps(industries or []),
        half_life_hours=half_life_hours,
        body=body.strip()
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    last_err = None
    for attempt in range(retries + 1):
        try:
            resp = client.chat(
                model=model,
                messages=messages,
                temperature=temperature,
                # 如果支援：保證 JSON
                response_format={"type": "json_object"},
            )
            raw_text = resp["content"]
            text = coerce_json(raw_text)
            data = json.loads(text)

            # ---- 計算 decayed_weight（若模型未算或算錯） ----
            age_hours = None
            if published_at is not None:
                now = datetime.now(timezone.utc)
                pub = published_at if published_at.tzinfo else published_at.replace(tzinfo=timezone.utc)
                age_hours = max(0.0, (now - pub).total_seconds() / 3600.0)

            if "scores" in data:
                if age_hours is None:
                    data["scores"]["decayed_weight"] = 1.0
                else:
                    hl = data["scores"].get("decay_half_life_hours", half_life_hours) or half_life_hours
                    data["scores"]["decayed_weight"] = round(math.exp(-age_hours / float(hl)), 6)
            else:
                data["scores"] = {
                    "impact_score": 0.5,
                    "sentiment_score": data.get("sentiment_overall", 0.0),
                    "novelty_score": 0.5,
                    "credibility_score": 0.5,
                    "decay_half_life_hours": half_life_hours,
                    "decayed_weight": 1.0 if age_hours is None else round(math.exp(-age_hours / float(half_life_hours)), 6),
                }

            # ---- 補充 metadata & raw_model ----
            data.setdefault("item_id", item_id)
            data.setdefault("source_url", source_url)
            data.setdefault("published_at", published_at.isoformat() if published_at else None)
            data.setdefault("tickers", tickers or [])
            data.setdefault("industries", industries or [])

            data["raw_model"] = {
                "reasoning_excerpt": (resp.get("reasoning_content") or "")[:4000],
            }
            data["model_name"] = resp["model"]
            data["model_latency_ms"] = resp["latency_ms"]

            # ---- 驗證 ----
            return NewsScores(**data)

        except (json.JSONDecodeError, ValidationError, RuntimeError) as e:
            last_err = e
            if attempt < retries:
                time.sleep(0.8 * (attempt + 1))
                continue
            raise

    # 正常不會到呢度
    if last_err:
        raise last_err


# =========================
# 方便你在 Django 任務 / command 內呼叫的函式
# =========================

def score_news_item(
    item_id: str,
    body: str,
    source_url: Optional[str],
    published_at: Optional[datetime],
    tickers: List[str],
    industries: List[str],
    model: str = "deepseek-reasoner",
    half_life_hours: int = 72,
) -> Dict[str, Any]:
    """
    Wrapper：回傳 dict（已通過 Pydantic），可直接存 DB 或發送到 message queue。
    """
    scores = extract_news_scores(
        item_id=item_id,
        body=body,
        source_url=source_url,
        published_at=published_at,
        tickers=tickers,
        industries=industries,
        model=model,
        half_life_hours=half_life_hours,
    )
    # 使用 mode='json' 確保所有對象都能正確序列化
    return scores.model_dump(mode='json')