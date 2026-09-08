#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
supabase_integration.py — وصلات أساسية مع Supabase
للمشروع: alforaijboard / bwspcsiazbwrrxpgoldx

الأعمدة الواقعية في الجدول market_listings (تم التأكد عبرHTTP query 2026-09-07):
  id, code, source, transaction, governorate, area,
  property_type, detail_class, price, price_text, space,
  listing_mode, summary, features,
  published_date, original_url, fetched_at,
  created_at, phone, last_seen_at, status,
  duplicate_of, source_id

ملاحظة: لا يوجد عمود 'location' — يستخدم 'area' كبديل.
ولا يوجد 'updated_at' — يستخدم 'last_seen_at' كبديل.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Optional

try:
    import requests
except ImportError:
    print("❌ يلزم تثبيت requests: pip install requests")
    sys.exit(1)


# ─── الإعدادات ────────────────────────────────────────────────────────────────

SUPABASE_URL = os.environ.get(
    "SUPABASE_URL",
    "https://bwspcsiazbwrrxpgoldx.supabase.co"
)

# prioritise service key for write access; fallback to anon
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get(
    "SUPABASE_ANON_KEY", ""
)

if not SUPABASE_KEY:
    print("❌ SUPABASE_KEY غير موجودة في الـ env")
    sys.exit(1)

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal",
}

TIMEOUT = 15  # ثواني


# ─── دوال مساعدة ─────────────────────────────────────────────────────────────

def _handle_response(response: requests.Response) -> Optional[list]:
    """تحويل الـ response إلى JSON أو log خطأ."""
    if response.status_code in (200, 201):
        try:
            return response.json()
        except ValueError:
            return []
    print(f"[SUPABASE] HTTP {response.status_code} — {response.text[:200]}")
    return None


def _filter_none_values(data: dict) -> dict:
    """إزالة القيم None من dict قبل الإرسال."""
    return {k: v for k, v in data.items() if v is not None}


# ─── الأعمدة الواقعية (مُثبتة بياناتً) ───────────────────────────────────────

DEFAULT_COLUMNS = [
    "id", "code", "source", "transaction", "governorate", "area",
    "property_type", "detail_class", "price", "price_text", "space",
    "listing_mode", "summary", "features",
    "published_date", "original_url", "fetched_at",
    "created_at", "phone", "last_seen_at", "status",
    "duplicate_of", "source_id",
]


# ─── استعلامات القراءة ────────────────────────────────────────────────────────

def fetch_listings(
    limit: int = 100,
    offset: int = 0,
    extra_cols: Optional[list[str]] = None,
) -> Optional[list[dict]]:
    """جلب listings من market_listings."""
    cols = extra_cols or DEFAULT_COLUMNS
    params = {
        "select": ",".join(cols),
        "limit": limit,
        "offset": offset,
        "order": "created_at.desc",
        "status": "eq.active",
    }
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/market_listings",
        headers=HEADERS, params=params, timeout=TIMEOUT,
    )
    return _handle_response(resp)


def fetch_listing_by_id(listing_id: str) -> Optional[dict]:
    """جلب listing واحد بمعرفه."""
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/market_listings?id=eq.{listing_id}",
        headers=HEADERS, timeout=TIMEOUT,
    )
    data = _handle_response(resp)
    return data[0] if data else None


def fetch_recent_activity(days: int = 7, limit: int = 50) -> Optional[list]:
    """الإعلانات/التغييرات últimas n días (حسب last_seen_at)."""
    since = (datetime.now() - timedelta(days=days)).isoformat()
    params = {
        "select": ",".join(DEFAULT_COLUMNS),
        "last_seen_at": f"gt.{since}",
        "order": "last_seen_at.desc",
        "limit": limit,
    }
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/market_listings",
        headers=HEADERS, params=params, timeout=TIMEOUT,
    )
    return _handle_response(resp)


def fetch_listing_count() -> Optional[int]:
    """عدد الإعلانات النشطة."""
    resp = requests.get(
        f"{SUPABASE_URL}/rest/v1/market_listings?select=count&status=eq.active",
        headers=HEADERS, timeout=TIMEOUT,
    )
    data = _handle_response(resp)
    if data and isinstance(data, list) and len(data) > 0:
        return data[0].get("count") or 0
    return None


# ─── عمليات الكتابة (إذا توفّر Service Key) ────────────────────────────────

def insert_listing(data: dict) -> Optional[dict]:
    """إضافة إعلان جديد."""
    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/market_listings",
        headers=HEADERS,
        json=_filter_none_values(data),
        timeout=TIMEOUT,
    )
    return _handle_response(resp)


def update_listing(listing_id: str, data: dict) -> Optional[dict]:
    """تحديث إعلان موجود (by id)."""
    resp = requests.patch(
        f"{SUPABASE_URL}/rest/v1/market_listings?id=eq.{listing_id}",
        headers=HEADERS,
        json=_filter_none_values(data),
        timeout=TIMEOUT,
    )
    return _handle_response(resp)


def delete_listing(listing_id: str) -> Optional[dict]:
    """حذف إعلان."""
    resp = requests.delete(
        f"{SUPABASE_URL}/rest/v1/market_listings?id=eq.{listing_id}",
        headers=HEADERS, timeout=TIMEOUT,
    )
    return _handle_response(resp)


# ─── دالة المساعدة السريعة ────────────────────────────────────────────────────

def quick_status() -> dict[str, Any]:
    """فحص سريع: هل الوصلة تعمل؟ وعدد الإعلانات؟"""
    count = fetch_listing_count()
    return {
        "supabase_url": SUPABASE_URL,
        "connected": count is not None,
        "listing_count": count,
        "key_available": bool(SUPABASE_KEY),
        "key_type": "service" if os.environ.get("SUPABASE_SERVICE_KEY") else "anon",
        "checked_at": datetime.now().isoformat(),
    }


# ─── الوضع التفاعلي ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🔍 فحص الوصلة مع Supabase...")
    status = quick_status()
    print(f"  URL       : {status['supabase_url']}")
    print(f"  Type Key  : {status['key_type']}")
    print(f"  متصل؟    : {status['connected']}")
    if status['connected']:
        print(f"  عدد الإعلانات النشطة: ~{status['listing_count']}")
        sample = fetch_listings(limit=3)
        if sample:
            print("  عيّنة منها:")
            for item in sample:
                area = item.get("area", "?") or item.get("governorate", "?")
                price = item.get("price")
                ptype = item.get("property_type", "?")
                print(f"    • {ptype} — {area} — {price}")
    else:
        print("  ⚠️ لا يمكن الوصول لقاعدة البيانات")
