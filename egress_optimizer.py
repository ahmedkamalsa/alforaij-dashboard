#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
egress_optimizer.py — نظام تقليل Egress عبر الكاش المحلي
يقلل المكالمات إلى Supabase ويخزن نسخة محلية
المشروع: alforaijboard / bwspcsiazbwrrxpgoldx
"""

import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    print("[#] يلزم تثبيت requests: pip install requests"); sys.exit(1)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from supabase_integration import fetch_listings, quick_status


# ─── إعدادات ────────────────────────────────────────────────────────────────

PROJECT_DIR = Path(__file__).resolve().parent
CACHE_DIR = PROJECT_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

LISTINGS_CACHE = CACHE_DIR / "listings_cache.json"
SUMMARY_CACHE = CACHE_DIR / "summary_cache.json"

REFRESH_INTERVAL_HOURS = 6


# ─── دوال الكاش ────────────────────────────────────────────────────────────

def get_cache_age(cache_path: Path) -> Optional[float]:
    if not cache_path.exists():
        return None
    age_seconds = (datetime.now() - datetime.fromtimestamp(cache_path.stat().st_mtime)).total_seconds()
    return age_seconds / 3600


def is_cache_fresh(cache_path: Path, max_age_hours: float = REFRESH_INTERVAL_HOURS) -> bool:
    age = get_cache_age(cache_path)
    if age is None:
        return False
    return age < max_age_hours


def save_to_cache(data, cache_path: Path) -> None:
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_from_cache(cache_path: Path):
    if not cache_path.exists():
        return None
    with open(cache_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ─── وحدات الكاش ────────────────────────────────────────────────────────────

def get_cached_listings(force_refresh: bool = False) -> Optional[list]:
    """
    جلب الإعلانات من الكاش إن كان حديثًا.
    إن لم يكن، جرب Supabase وحدث الكاش.
    """
    if not force_refresh and is_cache_fresh(LISTINGS_CACHE):
        listings = load_from_cache(LISTINGS_CACHE)
        print(f"[OK] Using cached listings ({len(listings) if listings else 0} items)")
        return listings
    
    print("[INFO] Fetching from Supabase (cache miss/stale)...")
    listings = fetch_listings(limit=300, extra_cols=[
        "id", "price", "area", "property_type", "governorate",
        "created_at", "status", "code", "source",
    ])
    
    if listings:
        save_to_cache(listings, LISTINGS_CACHE)
        print(f"[INFO] Cached {len(listings)} listings")
    
    return listings


def get_cached_summary(force_refresh: bool = False) -> Optional[dict]:
    """
    جلب ملخص السوق من الكاش.
    """
    if not force_refresh and is_cache_fresh(SUMMARY_CACHE, max_age_hours=2):
        summary = load_from_cache(SUMMARY_CACHE)
        print("[OK] Using cached summary")
        return summary
    
    listings = get_cached_listings(force_refresh=force_refresh)
    if not listings:
        return None
    
    areas = Counter(item.get("area") or "غير معروف" for item in listings)
    types = Counter(item.get("property_type") or "غير معروف" for item in listings)
    prices = [item.get("price") for item in listings if item.get("price")]
    
    summary = {
        "generated_at": datetime.now().isoformat(),
        "total_listings": len(listings),
        "avg_price": round(sum(prices) / len(prices)) if prices else 0,
        "min_price": round(min(prices)) if prices else 0,
        "max_price": round(max(prices)) if prices else 0,
        "top_areas": areas.most_common(10),
        "top_types": types.most_common(5),
        "cache_fresh_until": (datetime.now() + timedelta(hours=REFRESH_INTERVAL_HOURS)).isoformat(),
    }
    
    save_to_cache(summary, SUMMARY_CACHE)
    print("[INFO] Summary cached")
    return summary


# ─── التشغيل ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("Egress Optimizer - Local Cache System")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print()
    
    # فحص Supabase
    print("1. Checking Supabase connection...")
    status = quick_status()
    if not status["connected"]:
        print("[ERROR] Supabase not connected")
        sys.exit(1)
    print(f"[OK] Connected - ~{status.get('listing_count')} listings")
    
    # جرب الكاش
    print("\n2. Trying cache...")
    summary = get_cached_summary()
    
    if summary:
        print("\n[SUCCESS] Report from cache:")
        print(f"  - Listings: {summary['total_listings']}")
        print(f"  - Average price: {summary['avg_price']:,} KWD")
        print(f"  - Price range: {summary['min_price']:,} - {summary['max_price']:,} KWD")
        print(f"  - Top 3 areas: {[a[0] for a in summary['top_areas'][:3]]}")
        print(f"  - Top types: {[t[0] for t in summary['top_types'][:3]]}")
    else:
        print("\n[INFO] No cache found - creating...")
        auto_summary = get_cached_summary(force_refresh=True)
        if auto_summary:
            print(f"\n[SUCCESS] After update:")
            print(f"  - Listings: {auto_summary['total_listings']}")
            print(f"  - Average price: {auto_summary['avg_price']:,} KWD")
    
    # تقرير
    print("\n" + "=" * 60)
    print("Egress Savings Report")
    print("=" * 60)
    print("  Each cache read saves ~40KB of egress")
    print("  Cache refreshes every 6 hours automatically")
    print("  Using 'get_cached_listings()' instead of 'fetch_listings()'")
    print("  Using 'get_cached_summary()' for quick reports")
    print("=" * 60)
