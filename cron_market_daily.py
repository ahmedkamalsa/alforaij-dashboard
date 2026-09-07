#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cron_market_daily.py — كرون يومي للتقارير والمراقبة
يستخدم Supabase + Local LLM
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
    print("❌ يلزم تثبيت requests: pip install requests")
    sys.exit(1)

# استيراد الوحدات المحلية
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from supabase_integration import fetch_listings, fetch_listing_count, quick_status
    from local_api import chat
    from market_analyzer import generate_daily_report
except ImportError as exc:
    print(f"❌ خطأ في استيراد الوحدات: {exc}")
    print("تأكد أن supabase_integration.py و local_api.py و market_analyzer.py في نفس المجلد.")
    sys.exit(1)


# ─── إعدادات المسارات ─────────────────────────────────────────────────────

PROJECT_DIR = Path(__file__).resolve().parent
LOG_DIR = PROJECT_DIR / "cron_logs"
REPORT_DIR = PROJECT_DIR / "reports"
NOTIFY_DIR = PROJECT_DIR / "notifications"

LOG_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)
NOTIFY_DIR.mkdir(parents=True, exist_ok=True)


def write_log(entry: dict) -> None:
    """اكتب سطر log."""
    log_path = LOG_DIR / "cron_events.jsonl"
    entry["_timestamp"] = datetime.now().isoformat()
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def notify(name: str, message: str) -> None:
    """احفظ إشعار محلي."""
    notif_path = NOTIFY_DIR / f"{name}.json"
    data = {
        "name": name,
        "message": message,
        "time": datetime.now().isoformat(),
    }
    with open(notif_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


# ─── الكرون ───────────────────────────────────────────────────────────────

def run_daily_cron() -> bool:
    """
    كرون يومي:
    1. فحص الـ API
    2. فحصSupabase
    3. جمع البيانات
    4. تحليل السوق
    5. حفظ التقرير
    6. إشعار
    """
    start = datetime.now()
    write_log({"event": "cron_start", "time": start.isoformat()})

    print(f"⏰ كرون السوق اليومي — {start.strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # 1. فحص الـ API
    print("\n1. فحص الـ Local LLM API...")
    try:
        from local_api import quick_status as api_status_fn
        api_info = api_status_fn()
        api_online = api_info["online"]
        print(f"   {'✅ متصل' if api_online else '❌ غير متصل'} — {api_info['model_count']} نموذج")
        write_log({"event": "api_check", "status": "online" if api_online else "offline", "models": api_info["models"]})
    except Exception as e:
        api_online = False
        print(f"   ❌ خطأ في فحص الـ API: {e}")
        write_log({"event": "api_check", "status": "error", "error": str(e)})

    # 2. فحص Supabase
    print("\n2. فحص Supabase...")
    try:
        sb_info = quick_status()
        sb_connected = sb_info["connected"]
        print(f"   {'✅ متصل' if sb_connected else '❌ غير متصل'} — {sb_info.get('listing_count', '؟')} إعلان")
        write_log({"event": "supabase_check", "status": "online" if sb_connected else "offline"})
    except Exception as e:
        sb_connected = False
        print(f"   ❌ خطأ في Supabase: {e}")
        write_log({"event": "supabase_check", "status": "error", "error": str(e)})

    if not api_online or not sb_connected:
        print("\n⚠️ لا يمكن المتابعة — API أو Supabase غير متاح.")
        write_log({"event": "cron_aborted", "reason": "api_or_supabase_unavailable"})
        return False

    # 3. جلب البيانات
    print("\n3. جلب بيانات السوق...")
    try:
        listings = fetch_listings(limit=200)
        if not listings:
            print("   ⚠لا توجد إعلانات")
            write_log({"event": "fetch_listings", "count": 0})
        else:
            print(f"   ✅ جُلبت {len(listings)} إعلان")
            write_log({"event": "fetch_listings", "count": len(listings)})
    except Exception as e:
        print(f"   ❌ خطأ في جلب الإعلانات: {e}")
        write_log({"event": "fetch_listings_error", "error": str(e)})
        return False

    # 4. التحليل
    print("\n4. تحليل السوق...")
    try:
        report = generate_daily_report(listings)
        if not report:
            print("   ❌ فاشل في توليد التقرير")
            write_log({"event": "generate_report", "status": "failed"})
            return False
        print("   ✅ تم توليد التقرير")
        write_log({"event": "generate_report", "status": "success"})
    except Exception as e:
        print(f"   ❌ خطأ في التحليل: {e}")
        write_log({"event": "generate_report_error", "error": str(e)})
        return False

    # 5. حفظ التقرير
    print("\n5. حفظ التقرير...")
    try:
        today_str = datetime.now().strftime("%Y-%m-%d")
        report_path = REPORT_DIR / f"market_report_{today_str}.txt"
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write(report)
        size_kb = os.path.getsize(report_path) // 1024
        print(f"   ✅ Report saved: {report_path} ({size_kb} KB)")
        write_log({"event": "save_report", "path": str(report_path), "size_kb": size_kb})
    except Exception as e:
        print(f"   ❌ خطأ في حفظ التقرير: {e}")
        write_log({"event": "save_report_error", "error": str(e)})
        return False

    # 6. إشعار
    print("\n6. إعداد الإشعار...")
    try:
        notify(
            "daily_market_report",
            f"✅ تقرير السوق العقاري اليومي جاهز. تم تحليل {len(listings)} إعلان. "
            f"الرجاء الاطلاع على التقرير."
        )
        print("   ✅ Notification saved")
        write_log({"event": "notification", "name": "daily_market_report"})
    except Exception as e:
        print(f"   ⚠لم يُحفظ الإشعار: {e}")
        write_log({"event": "notification_error", "error": str(e)})

    end = datetime.now()
    duration = (end - start).total_seconds()
    print(f"\n⏱️ المدة: {duration:.1f} ثانية")
    print("=" * 60)
    write_log({"event": "cron_complete", "duration_sec": duration})

    return True


# ─── التنفيذ ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        success = run_daily_cron()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️ متوقف يدوياً")
        sys.exit(1)
    except Exception as exc:
        print(f"\n❌ خطأ غير متوقع: {exc}")
        write_log({"event": "cron_unexpected_error", "error": str(exc)})
        sys.exit(1)
