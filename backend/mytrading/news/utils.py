# apps/news/utils.py
import hashlib, re
from datetime import datetime, timezone
import trafilatura
from langdetect import detect

def extract_main_text(html_or_text: str) -> str | None:
    # trafilatura 對 HTML/全文均可嘗試
    txt = trafilatura.extract(html_or_text, include_comments=False, include_tables=False)
    if not txt:
        # 後備：去除多餘空白
        txt = re.sub(r"\s+", " ", html_or_text or "").strip()
    if txt and len(txt) < 200:  # 太短嘅就放棄
        return None
    return txt

def detect_lang(text: str, fallback="en") -> str:
    try:
        return detect(text) or fallback
    except Exception:
        return fallback

def sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def chunk_text(text: str, max_chars=1200, overlap=150):
    # 以字數近似切塊（簡潔穩定），避免長度過長
    if len(text) <= max_chars:
        return [text]
    chunks = []
    i = 0
    while i < len(text):
        end = min(len(text), i + max_chars)
        chunk = text[i:end]
        chunks.append(chunk)
        if end == len(text):
            break
        i = end - overlap
        if i < 0: i = 0
    return chunks

def now_utc():
    return datetime.now(timezone.utc)