# research/llm_client.py
import os, json
from typing import Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential
from openai import OpenAI

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,  # DeepSeek 為 OpenAI-compatible
)

SYS_JSON_ONLY = (
    "你是一名金融分析師，只能輸出有效 JSON，不可加入任何說明、標點或 Markdown。"
    "若不確定數值，請以 null/估算並標示 is_estimate=true。"
)

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
def llm_json(prompt: str) -> Dict[str, Any]:
    """
    呼叫 DeepSeek，要求返回 JSON。失敗會重試。
    """
    rsp = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        temperature=0.2,
        messages=[
            {"role":"system","content":SYS_JSON_ONLY},
            {"role":"user","content":prompt},
        ],
        response_format={"type":"json_object"},  # OpenAI SDK 支援 JSON 強制
    )
    txt = rsp.choices[0].message.content
    return json.loads(txt)