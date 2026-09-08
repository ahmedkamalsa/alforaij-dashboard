#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
monitor.py — نظام مراقبة صحة النظام
يتحقق دوريًا من:
1. الـ Local LLM API
2. Supabase
3. وجود السكربتات الأساسية
4. سجل الأخطاء الأخير
5. مرنية التقرير

يُستخدم كحاوية Docker أو سكربت مستقل
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    import requests
except ImportError:
    print("❌ يلزم تثبيت requests: pip install requests"); sys.exit(1)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from supabase_integration import quick_status as sb_status
from local_api import quick_status as api_status


# ─── إعدادات المسارات ─────────────────────────────────────────────────────

PROJECT_DIR = Path(__file__).resolve().parent
LOG_DIR = PROJECT_DIR / "cron_logs"
NOTIFY_DIR = PROJECT_DIR / "notifications"
HEALTH_LOG = LOG_DIR / "health_check.jsonl"

LOG_DIR.mkdir(parents=True, exist_ok=True)
NOTIFY_DIR.mkdir(parents=True, exist_ok=True)
HEALTH_LOG.touch(exist_ok=True)


def log_health(health_data: dict) -> None:
    """اكتب نتيجة الفحص في سجل الصحة."""
    health_data["_timestamp"] = datetime.now().isoformat()
    with open(HEALTH_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(health_data, ensure_ascii=False) + "\n")


def notify_critical(message: str) -> None:
    """احفظ إشعار تنبيه حرج."""
    notif_path = NOTIFY_DIR / "alert_critical.json"
    data = {
        "name": "critical_alert",
        "message": message,
        "time": datetime.now().isoformat(),
        "severity": "critical",
    }
    with open(notif_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def check_all() -> dict[str, Any]:
    """فحص شامل لكل مكونات النظام."""
    start = datetime.now()
    results = {
        "timestamp": start.isoformat(),
        "components": {},
        "overall_status": "healthy",
        "issues": [],
    }

    # 1. فحص الـ Local API
    try:
        api = api_status()
        api_online = api["online"]
        results["components"]["local_llm_api"] = {
            "status": "online" if api_online else "offline",
            "models": api["models"],
            "model_count": len(api["models"]),
        }
        if not api_online:
            results["overall_status"] = "degraded"
            results["issues"].append("Local LLM API غير متاح")
    except Exception as e:
        results["components"]["local_llm_api"] = {"status": "error", "error": str(e)}
        results["overall_status"] = "unhealthy"
        results["issues"].append(f"Local LLM API خطأ: {e}")

    # 2. فحص Supabase
    try:
        sb = sb_status()
        sb_connected = sb["connected"]
        results["components"]["supabase"] = {
            "status": "online" if sb_connected else "offline",
            "listing_count": sb.get("listing_count"),
        }
        if not sb_connected:
            results["overall_status"] = "degraded"
            results["issues"].append("Supabase غير متاح")
    except Exception as e:
        results["components"]["supabase"] = {"status": "error", "error": str(e)}
        results["overall_status"] = "unhealthy"
        results["issues"].append(f"Supabase خطأ: {e}")

    # فحص الوقت المنقضي من آخر كرون (من سجل المراقبة)
    try:
        if HEALTH_LOG.exists() and HEALTH_LOG.stat().st_size > 0:
            lines = HEALTH_LOG.read_text(encoding="utf-8").strip().split("\n")
            # filtr lines غير الفارغة
            non_empty = [ln for ln in lines if ln.strip()]
            if non_empty:
                last_entry = json.loads(non_empty[-1])
                last_time = datetime.fromisoformat(last_entry.get("_timestamp", "2000-01-01"))
                minutes_ago = (start - last_time).total_seconds() / 60
                results["components"]["last_cron"] = {
                    "minutes_ago": round(minutes_ago),
                    "status": "recent" if minutes_ago < 15 else "stale",
                }
                if minutes_ago > 30:
                    results["issues"].append(f"الكرون الأخير منذ {minutes_ago:.0f} دقيقة")
            else:
                results["components"]["last_cron"] = {"status": "no_data"}
        else:
            results["components"]["last_cron"] = {"status": "no_data", "note": "سجل فارغ"}
    except Exception as e:
        results["components"]["last_cron"] = {"status": "error", "error": str(e)}

    # 4. فحص الملفات الأساسية
    essential_files = [
        "supabase_integration.py",
        "local_api.py",
        "market_analyzer.py",
        "cron_market_daily.py",
        "update_live_db.py",
    ]
    for fname in essential_files:
        fpath = PROJECT_DIR / fname
        exists = fpath.is_file()
        results["components"].setdefault("essential_files", {})[fname] = {
            "exists": exists,
            "size_kb": fpath.stat().st_size // 1024 if exists else 0,
        }
        if not exists:
            results["issues"].append(f"ملف مفقود: {fname}")

    # 4. فحص مساحة القرص
    try:
        import shutil
        usage = shutil.disk_usage(str(PROJECT_DIR))
        free_mb = usage.free // (1024 * 1024)
        results["components"]["disk"] = {
            "free_mb": free_mb,
            "status": "ok" if free_mb > 500 else "low" if free_mb > 100 else "critical",
        }
        if free_mb < 200:
            results["issues"].append(f"مساحة قرص منخفضة: {free_mb} MB")
    except Exception as e:
        results["components"]["disk"] = {"status": "error", "error": str(e)}

    # تحديد الوضع الكلي
    if results["issues"]:
        if results["overall_status"] == "healthy":
            results["overall_status"] = "degraded"
    # إذا كل شيء healthy stuck intact

    return results


def format_report(health: dict) -> str:
    """تنسيق تقرير المراقبة."""
    lines = [
        "🏥 تقرير المراقبة",
        "=" * 40,
        f"الوقت: {health['timestamp']}",
        f"الحالة الكلية: {health['overall_status']}",
        "",
        "المكونات:",
    ]
    for name, info in health.get("components", {}).items():
        status_icon = "✅" if info.get("status") == "online" or info.get("status") == "ok" else \
                      "⚠️" if info.get("status") == "degraded" or info.get("status") == "recent" or \
                           info.get("status") == "stale" or info.get("status") == "low" else \
                      "❌" if info.get("status") == "offline" or info.get("status") == "error" or \
                           info.get("status") == "critical" or info.get("status") == "unhealthy" else "🔍"
        if isinstance(info, dict):
            if "status" in info:
                lines.append(f"  {status_icon} {name}: {info['status']}")
            if "error" in info:
                lines.append(f"     خطأ: {info['error'][:100]}")
            if "models" in info:
                lines.append(f"     الموديلات: {len(info['models'])}")
            if "listing_count" in info:
                lines.append(f"     الإعلانات: ~{info['listing_count']}")
            if "minutes_ago" in info:
                lines.append(f"     منذ آخر كرون: {info['minutes_ago']} دقيقة")
            if "free_mb" in info:
                lines.append(f"     مساحة القرص المجانية: {info['free_mb']} MB")
            if "exists" in info:
                lines.append(f"     موجود: {'✅' if info['exists'] else '❌'} ({info.get('size_kb', 0)} KB)")
    
    if health.get("issues"):
        lines.append("")
        lines.append("⚠️ مشاكل:")
        for issue in health["issues"]:
            lines.append(f"  • {issue}")
    
    return "\n".join(lines)


def run_monitor():
    """تشغيل المراقبة."""
    print(f"🔍 فحص صحة النظام — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 40)
    
    health = check_all()
    report = format_report(health)
    print(report)
    
    # حفظ السجل
    log_health(health)
    
    # إذا كانت الحالة حرجة، إنشاء إشعار
    if health["overall_status"] == "unhealthy":
        notify_critical("النظام في حالة غير صحية — Immediate attention required")
        print("\n🆘 تم إنشاء إشعار لحالة حرجة")
    
    # إرجاع كود الخروج المناسب
    if health["overall_status"] == "healthy":
        return 0
    elif health["overall_status"] == "degraded":
        return 1
    else:
        return 2


if __name__ == "__main__":
    try:
        exit_code = run_monitor()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️ متوقف"); sys.exit(1)
    except Exception as exc:
        print(f"\n❌ خطأ: {exc}")
        log_health({"event": "monitor_error", "error": str(exc)})
        sys.exit(2)
