#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_live_db.py — تحديث ملف live-db.json من Supabase
يُستخدم في تحديث بيانات الموقع بانتظام
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from collections import Counter

try:
    import requests
except ImportError:
    print("❌ يلزم تثبيت requests: pip install requests"); raise

sys.path.insert(0, str(Path(__file__).resolve().parent))
from supabase_integration import fetch_listings, fetch_listing_count, quick_status


# ─── إعدادات ────────────────────────────────────────────────────────────────

PROJECT_DIR = Path(__file__).resolve().parent
SITE_DIR = PROJECT_DIR / "site"
STATIC_DATA_DIR = SITE_DIR / "static-data"
LIVE_DB_PATH = STATIC_DATA_DIR / "live-db.json"

STATIC_DATA_DIR.mkdir(parents=True, exist_ok=True)


def fetch_active_listings(limit: int = 3000) -> list[dict]:
    """جلب جميع الإعلانات النشطة."""
    return fetch_listings(limit=limit) or []


def build_live_db(listings: list[dict]) -> dict:
    """بناء ملف live-db.json من listings."""
    total = len(listings)
    active_count = sum(1 for item in listings if item.get("status") == "active")
    
    # تحليل 퀵
    areas = Counter(item.get("area") or "غير معروف" for item in listings)
    types = Counter(item.get("property_type") or "غير معروف" for item in listings)
    prices = [item.get("price") for item in listings if item.get("price")]
    avg_price = sum(prices) / len(prices) if prices else 0
    max_price = max(prices) if prices else 0
    min_price = min(prices) if prices else 0
    
    # أعلى 10 مناطق
    top_areas = areas.most_common(10)
    top_types = types.most_common(5)
    
    return {
        "last_updated": datetime.now().isoformat(),
        "total_count": total,
        "active_count": active_count,
        "summary": {
            "average_price": round(avg_price),
            "min_price": round(min_price),
            "max_price": round(max_price),
            "top_areas": [{"area": a, "count": c} for a, c in top_areas],
            "top_types": [{"type": t, "count": c} for t, c in top_types],
            "price_range": {"min": round(min_price), "max": round(max_price)},
        },
        "listings": listings,
    }


def save_live_db(data: dict) -> Path:
    """حفظ ملف live-db.json."""
    path = LIVE_DB_PATH
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    return path


def run_update():
    """التشغيل الرئيسي."""
    start = datetime.now()
    print(f"🔄 تحديث قاعدة البيانات — {start.strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    # 1. فحص الوصلة
    print("\n1. فحص Supabase...")
    status = quick_status()
    print(f"   {'✅' if status['connected'] else '❌'} {'متصل' if status['connected'] else 'غير متصل'}")
    print(f"   إجمالي الإعلانات: ~{status.get('listing_count')}")
    
    if not status['connected']:
        print("   ❌ لا يمكن المتابعة")
        return False
    
    # 2. جلب البيانات
    print("\n2. جلب الإعلانات...")
    listings = fetch_active_listings(limit=3000)
    if not listings:
        print("   ⚠لا توجد إعلانات")
        return False
    print(f"   ✅ تم جلب {len(listings)} إعلان")
    
    # 3. بناء الـ live-db.json
    print("\n3. بناء ملف البيانات...")
    live_db = build_live_db(listings)
    path = save_live_db(live_db)
    print(f"   ✅ تم حفظ: {path}")
    print(f"   حجم الملف: {os.path.getsize(path) // 1024} KB")
    
    # 4. ملخص سريع
    print("\n" + "=" * 60)
    print("📊 ملخص البيانات:")
    print(f"   إجمالي الإعلانات: {live_db['total_count']}")
    print(f"   الإعلانات النشطة: {live_db['active_count']}")
    print(f"   المتوسط السعري: {live_db['summary']['average_price']:,.0f} دينار كويتي")
    print(f"   نطاق الأسعار: {live_db['summary']['min_price']:,.0f} – {live_db['summary']['max_price']:,.0f}")
    print(f"   أهم 3 مناطق: {[a['area'] for a in live_db['summary']['top_areas'][:3]]}")
    print("=" * 60)
    
    print(f"\n⏱️ المدة: {(datetime.now() - start).total_seconds():.1f} ثانية")
    return True


if __name__ == "__main__":
    try:
        success = run_update()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ متوقف"); exit(1)
    except Exception as exc:
        print(f"\n❌ خطأ: {exc}")
        exit(1)
