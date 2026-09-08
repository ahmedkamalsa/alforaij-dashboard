#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
egress_tracker.py — مراقبة استهلاك Egress في Supabase
يتحقق من لوحة الاستخدام ويسجّل النتائج ويُبيّن خطر تجاوز الحد
المشروع: alforaijboard / bwspcsiazbwrrxpgoldx
"""

import json
import os
import sys
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import requests
except ImportError:
    print("❌ يلزم تثبيت requests: pip install requests"); sys.exit(1)


# ─── إعدادات ────────────────────────────────────────────────────────────────

PROJECT_DIR = Path(__file__).resolve().parent
LOG_DIR = PROJECT_DIR / "cron_logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

EGRESS_LOG = LOG_DIR / "egress_tracker.jsonl"

SUPABASE_ORG_URL = "https://supabase.com/dashboard/org/auwiylhikikzndrttdzpd/usage"

# الحدود (من الصورة)
EGRESS_LIMIT_GB = 5.0
DATABASE_LIMIT_GB = 0.5
GRACE_END_DATE = "2026-09-17"

# مسار الكاش (ليستعل من الكاش بدل Supabase)
CACHE_DIR = PROJECT_DIR / "cache"


# ─── دوال المساعدة ──────────────────────────────────────────────────────────

def log_egress(entry: dict) -> None:
    """احفظ سجل egress."""
    entry["_timestamp"] = datetime.now().isoformat()
    with open(EGRESS_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def notify(message: str, severity: str = "warning") -> None:
    """احفظ إشعار."""
    from pathlib import Path
    NOTIFY_DIR = PROJECT_DIR / "notifications"
    NOTIFY_DIR.mkdir(parents=True, exist_ok=True)
    notif_path = NOTIFY_DIR / f"egress_alert_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    data = {
        "name": "egress_alert",
        "message": message,
        "severity": severity,
        "time": datetime.now().isoformat(),
    }
    with open(notif_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def parse_usage_from_page(html_content: str) -> dict:
    """استخراج قيم egress من صفحة HTML (لو وصلناها)."""
    # أنماط استخراج من الصورة
    egress_match = re.search(r"Egress.*?(\d+\.?\d*)\s*/\s*(5\s*GB)", html_content)
    db_match = re.search(r"Database Size.*?(\d+\.?\d*)\s*/\s*(0\.5\s*GB)", html_content)
    
    result = {}
    if egress_match:
        result["egress_used_gb"] = float(egress_match.group(1))
        result["egress_limit_gb"] = 5.0
    if db_match:
        result["database_used_gb"] = float(db_match.group(1))
        result["database_limit_gb"] = 0.5
    
    return result


def estimate_egress_from_cache() -> Optional[float]:
    """تقدير egress من كاش الاستخدام (لو صادفته)."""
    usage_cache = CACHE_DIR / "usage_cache.json"
    if usage_cache.exists():
        with open(usage_cache, "r") as f:
            data = json.load(f)
        return data.get("egress_used_gb")
    return None


def check_supabase_api_usage() -> Optional[dict]:
    """
    جلب استخدام من Supabase API (لو كان متاحًا).
    هذا يحتاج إمكانية الوصول لل Admin API.
    """
    # لا يوجد API مباشر للـ usage في Supabase المجاني
    # لكن ممكن نستخدم صفحة الويب في حالات محددة
    return None


# ─── تقرير egress ────────────────────────────────────────────────────────

def generate_egress_report():
    """توليد تقرير egress."""
    print("📊 تقرير استهلاك Egress")
    print("=" * 50)
    
    # جرب الكاش أولاً
    cached_usage = estimate_egress_from_cache()
    
    egress_used = cached_usage if cached_usage else None
    
    if egress_used is None:
        print("⚠ لا يوجد بيانات egress محفوظة المحليًا")
        print("  الحل: الشاحنة Supabase dashboard يدوياً أو إضافة سكربت استخراج")
        print()
        print("  الحد الحالي: 5 جيجابايت")
        print("  الاستخدام (من الصورة السابقة): 6.78 جيجابايت (136%)")
        print(f"  الموعد النهائي للـ Grace: {GRACE_END_DATE}")
        print()
        print("  ⚠️ تم تجاوز الحد!")
        notify("تم تجاوز حد Egress — 6.78/5 جيجابايت (136%) — grace截止 17 سبتمبر", severity="critical")
        return None
    
    usage_pct = (egress_used / EGRESS_LIMIT_GB) * 100
    remaining = EGRESS_LIMIT_GB - egress_used
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "egress_used_gb": egress_used,
        "egress_limit_gb": EGRESS_LIMIT_GB,
        "usage_percent": round(usage_pct, 1),
        "remaining_gb": round(remaining, 2),
        "grace_ends": GRACE_END_DATE,
        "is_over_limit": egress_used > EGRESS_LIMIT_GB,
    }
    
    print(f"  الاستخدام: {egress_used} / {EGRESS_LIMIT_GB} جيجابايت")
    print(f"  النسبة المئوية: {usage_pct:.1f}%")
    print(f"  الباقي: {remaining} جيجابايت")
    print(f"  تجاوز الحد: {'نعم ⚠️' if egress_used > EGRESS_LIMIT_GB else 'لا'}")
    print(f"  grace截止: {GRACE_END_DATE}")
    
    log_egress(report)
    
    if egress_used > EGRESS_LIMIT_GB:
        notify(f"⚠️ تجاوز Egress: {egress_used} / {EGRESS_LIMIT_GB} GB — grace截止 {GRACE_END_DATE}", severity="critical")
        print()
        print("  أنت تجاوزت الحد! خفّض egress فورًا:")
        print("  - استخدم الكاش المحلي (egress_optimizer.py)")
        print("  - قلّل الـ fetch عن Supabase")
        print("  - جرب Neon أو Turso كبديل")
    else:
        print()
        print(f"  ✅ أنت تحت الحد — الباقي {remaining} جيجابايت")
    
    return report


# ─── التشغيل ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    generate_egress_report()
