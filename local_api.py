#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
local_api.py — غلاف بسيط للـ Local LLM API (hermes-3-llama-3.1-8b)
الـ Endpoint: http://localhost:1234/v1/chat/completions
"""

import os
import sys
from typing import Optional

try:
    import requests
except ImportError:
    print("❌ يلزم تثبيت requests: pip install requests")
    sys.exit(1)

# ─── الإعدادات ────────────────────────────────────────────────────────────────

LOCAL_API_URL = os.environ.get(
    "LOCAL_API_URL", "http://localhost:1234/v1/chat/completions"
)
DEFAULT_MODEL = "hermes-3-llama-3.1-8b"
DEFAULT_TIMEOUT = 300  # ثواني — الموديل قد يحتاج وقتًا طويلًا للردود الكبيرة

# ─── دوال التواصل ────────────────────────────────────────────────────────────

def check_models() -> list[dict]:
    """الاستعلام عن النماذج المتاحة."""
    resp = requests.get(f"{LOCAL_API_URL.replace('/v1/chat/completions', '/v1/models')}")
    if resp.status_code == 200:
        data = resp.json()
        return data.get("data", [])
    print(f"[LOCAL_API] فشل جلب النماذج: {resp.status_code}")
    return []


def chat(
    prompt: str,
    model: str = DEFAULT_MODEL,
    system_message: Optional[str] = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    timeout: int = DEFAULT_TIMEOUT,
) -> Optional[str]:
    """
    إرسال رسالة واحدة لـ Local LLM والاستجابة.
    """
    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        resp = requests.post(LOCAL_API_URL, json=payload, timeout=timeout)
        if resp.status_code != 200:
            print(f"[LOCAL_API] HTTP {resp.status_code}: {resp.text[:200]}")
            return None
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except requests.Timeout:
        print(f"[LOCAL_API] انتهت المهلة ({timeout}s) — الموديل可能太的时间 طويل 토의다.")
        return None
    except Exception as e:
        print(f"[LOCAL_API] خطأ غير متوقع: {e}")
        return None


def chat_stream(
    prompt: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 1024,
):
    """
    دفق응답 (streaming) — يعيد مُخرِجاً ينتج tokens كما تصل.
    """
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }
    try:
        with requests.post(LOCAL_API_URL, json=payload, stream=True, timeout=timeout) as resp:
            if resp.status_code != 200:
                print(f"[LOCAL_API] HTTP {resp.status_code}")
                return
            for line in resp.iter_lines(decode_unicode=True):
                if line.startswith("data: "):
                    line = line[6:]
                    if line.strip() == "[DONE]":
                        break
                    try:
                        chunk = __import__("json").loads(line)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except Exception:
                        pass
    except Exception as e:
        print(f"[LOCAL_API] خطأ في الـ stream: {e}")


# ─── فحص سريع ───────────────────────────────────────────────────────────────

def quick_status():
    """هل الـ API عملي؟"""
    models = check_models()
    online = len(models) > 0
    return {
        "url": LOCAL_API_URL,
        "online": online,
        "model_count": len(models),
        "models": [m.get("id") for m in models],
    }


# ─── وضع التفاعل ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🔍 فحص الـ Local LLM API...")
    status = quick_status()
    print(f"  URL      : {status['url']}")
    print(f"  متصل؟   : {status['online']}")
    if status['online']:
        print(f"  عدد الموديلات: {status['model_count']}")
        for m in status['models']:
            print(f"    • {m}")
        print()
        print("📝 جرب 부설연구소:")
        test = chat("من أنت؟ اذكر ثلاث خصائص رئيسية")
        if test:
            print(f"  الردود: {test}")
        else:
            print("  ⚠لم يحصل على رد — ربما الموديل يحتاج وقتًا أطول أو جهاز أقتذر.")
    else:
        print("  ⚠️ الـ Local API غير متاح — تأكد من تشغيل LM Studio وLocal Server.")
