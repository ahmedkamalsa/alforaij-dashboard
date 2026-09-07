#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# market_analyzer.py
# تحليل السوق العقاري باستخدام Supabase + Local LLM

import os, sys, json, re
from typing import Optional
from collections import Counter
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import requests
except ImportError:
    print("❌ يلزم تثبيت requests: pip install requests"); sys.exit(1)

from supabase_integration import fetch_listings, fetch_listing_count, quick_status
from local_api import chat, quick_status as api_status

# ── إعدادات ──────────────────────────────────────────────────────────────

# استخدم أعمدة حقيقية من قاعدة البيانات
# الأعمدة المتاحة: id, title, description, price, property_type, location, 
# city, square_meters, bedrooms, bathrooms, created_at, updated_at, active
# حسب رسالة الخطأ السابقة، عمود "location" غير موجود - نستخدم city 대신

LISTING_FIELDS = [
    "id", "title", "description", "price", "property_type",
    "city", "square_meters", "bedrooms", "bathrooms",
    "created_at", "updated_at", "active"
]

# ── دوال المساعدة ──────────────────────────────────────────────────────

def sanitize_price(value) -> Optional[float]:
    """نظّف السعر extraction أرقام."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        nums = re.findall(r"[\d,]+", value.replace(",", ""))
        try:
            return float("".join(nums))
        except:
            return None
    return None

def summarize_listings(listings: list[dict]) -> str:
    """تلخيص listings في نص."""
    if not listings:
        return "لا توجد إعلانات."
    
    region_counter = Counter()
    price_vals = []
    type_counter = Counter()
    size_vals = []
    
    for item in listings:
        # city بدل location
        region = item.get("area") or item.get("governorate") or "غير معروف"
        region_counter[region] += 1
        
        price = sanitize_price(item.get("price"))
        if price:
            price_vals.append(price)
        
        ptype = item.get("property_type") or "غير معروف"
        type_counter[ptype] += 1
        
        size = item.get("square_meters")
        if size:
            try:
                size_vals.append(float(size))
            except:
                pass
    
    avg_price = sum(price_vals) / len(price_vals) if price_vals else 0
    max_price = max(price_vals) if price_vals else 0
    min_price = min(price_vals) if price_vals else 0
    
    avg_size = sum(size_vals) / len(size_vals) if size_vals else 0
    max_size = max(size_vals) if size_vals else 0
    
    top_regions = region_counter.most_common(5)
    top_types = type_counter.most_common(4)
    
    lines = [
        f"عدد الإعلانات: {len(listings)}",
        f"المتوسط السعري: {avg_price:,.0f} دينار كويتي",
        f"نطاق الأسعار: {min_price:,.0f} – {max_price:,.0f} دينار كويتي",
        f"المتوسط المساحي: {avg_size:,.0f} متر²",
        f"أبرز المساحات: حتى {max_size:,.0f} متر²",
        "",
        "أهم 5 مناطق:",
    ]
    for region, count in top_regions:
        lines.append(f"  • {region} — {count} إعلان")
    
    lines.append("")
    lines.append("أنواع العقارات الأكثر:")
    for ptype, count in top_types:
        lines.append(f"  • {ptype} — {count} إعلان")
    
    return "\n".join(lines)


def generate_market_analysis(listings: list[dict]) -> Optional[str]:
    """تحليل السوق الكامل بالـ Local LLM."""
    summary = summarize_listings(listings)
    
    prompt = f"""\
أنت محلل سوق عقاري خبير في الكويت.
قم بتحليل البيانات التالية للإعلانات العقارية:

{summary}

يرجى تقديم:
1. ملخص تنفيذي (3-4 أسطر)
2. تحليل المناطق الرابحة وسببية
3. ملاحظات عن الأسعار والمساحات
4. توقعات للسوق القادم (1-2 شهور)
5. نصائح للمستثمرين المبتدئين

الرد بالعربية الفصحى، واضح، واحترافي.
"""
    
    return chat(prompt, max_tokens=3072, temperature=0.3)


def generate_daily_report(listings: list[dict]) -> Optional[str]:
    """توليد تقرير يومي."""
    analysis = generate_market_analysis(listings)
    if not analysis:
        return "فشل في توليد التحليل."
    
    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    total = fetch_listing_count()
    
    report = f"""\
{'='*60}
📊 تقرير السوق العقاري — الكويت
{'='*60}
التاريخ: {today}
إجمالي الإعلانات في القاعدة: ~{total}
عدد الإعلانات المفعلة: {len(listings)}

{analysis}

{'='*60}
تقرير تم إنشاؤه تلقائيًا بواسطة نظام الذكاء الاصطناعي المحلي
الموديل: hermes-3-llama-3.1-8b
{'='*60}
"""
    return report


# ── التشغيل ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("🔎 تحليل السوق العقاري — الكويت")
    print("=" * 60)
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    status = quick_status()
    print(f"📦 Supabase : {'متصل' if status['connected'] else 'غير متصل'}")
    print(f"🤖 Local LLM: {'متصل' if api_status()['online'] else 'غير متصل'}")
    print()
    
    listings = fetch_listings(limit=200)
    if not listings:
        print("⚠️ لا توجد إعلانات للعرض.")
        sys.exit(0)
    
    print(f"📥 جُلبت {len(listings)} إعلان — جاري التحليل...")
    print()
    
    report = generate_daily_report(listings)
    if report:
        print(report)
    else:
        print("⚠️ فشل في توليد التقرير.")
    
    # حفظ للتقرير
    today = datetime.now().strftime("%Y-%m-%d")
    report_path = Path("reports") / f"market_report_{today}.txt"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n💾 Report: {report_path}")
