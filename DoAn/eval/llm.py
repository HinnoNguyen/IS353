"""Gọi LLM qua Groq (https://console.groq.com) cho các baseline. Cần GROQ_API_KEY trong DoAn/.env.

Mọi lần gọi thành công (prompt, output thô, số token, header hạn mức) được ghi thêm vào results/cache/groq_log.jsonl.
"""
import json
import math
import os
import time
from datetime import datetime
from pathlib import Path

import groq
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
LOG_PATH = ROOT / "results" / "cache" / "groq_log.jsonl"
MAX_RETRIES = 4
RETRYABLE = (groq.RateLimitError, groq.InternalServerError, groq.APIConnectionError)  # 429, 5xx, lỗi mạng

_client = None


class DailyLimitError(RuntimeError):
    """Hết hạn mức theo ngày (RPD/TPD): chờ vài phút không giải quyết được, phải dừng lượt chạy."""


def get_client():
    global _client
    if _client is None:
        # max_retries=0: tự thử lại trong groq_chat để chờ đúng retry-after và nhận ra lỗi hết hạn mức ngày
        _client = groq.Groq(api_key=os.environ["GROQ_API_KEY"], max_retries=0)
    return _client


def retry_after(e):
    try:
        return math.ceil(float(e.response.headers["retry-after"]))
    except (AttributeError, KeyError, TypeError, ValueError):
        return None


def groq_chat(model: str, prompt: str) -> str:
    """Gửi prompt thành 1 tin nhắn user với temperature 0, trả về nội dung trả lời ("" nếu rỗng)."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            raw = get_client().chat.completions.with_raw_response.create(
                model=model, temperature=0, messages=[{"role": "user", "content": prompt}])
            break
        except RETRYABLE as e:
            # vd. "Rate limit reached for model ... on tokens per day (TPD): Limit 500000, Used ..."
            if "per day" in str(e):
                raise DailyLimitError(str(e)) from e
            if attempt == MAX_RETRIES:
                raise
            wait = retry_after(e) or 30 * (attempt + 1)
            print(f"    Groq lỗi ({str(e)[:90]}), chờ {wait}s...")
            time.sleep(wait)
    resp = raw.parse()
    msg = resp.choices[0].message
    log = {"at": datetime.now().astimezone().isoformat(timespec="seconds"), "model": model,
           "model_returned": resp.model, "system_fingerprint": resp.system_fingerprint,
           "finish_reason": resp.choices[0].finish_reason, "prompt": prompt, "content": msg.content,
           "reasoning": getattr(msg, "reasoning", None),
           "usage": resp.usage.model_dump() if resp.usage else None,
           "ratelimit": {k: v for k, v in raw.headers.items() if k.startswith("x-ratelimit")}}
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(log, ensure_ascii=False, default=str) + "\n")
    return msg.content or ""
