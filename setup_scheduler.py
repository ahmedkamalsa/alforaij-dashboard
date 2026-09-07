#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
setup_scheduler.py — إنشاء مهام Windows Task Scheduler لأتمتة كاملة
المهام:
  1. Alforaijboard-MarketDaily — تحليل سوق يومي (09:00 يوميًا)
  2. Alforaijboard-UpdateLiveDB — تحديث قاعدة البيانات (06:00 يوميًا)
  3. Alforaijboard-SystemMonitor — مراقبة صحة النظام (كل ساعة)
  4. Alforaijboard-EgressCheck — مراقبة Egress Supabase (20:00 يوميًا)
"""

import subprocess
import sys
from pathlib import Path


PROJECT_DIR = Path(r"D:\foraj_social\287\alforaijboard")
PYTHON = "python"


TASKS = [
    {
        "tn": "Alforaijboard-MarketDaily",
        "command": f'cmd /c "cd /d {PROJECT_DIR} && {PYTHON} cron_market_daily.py"',
        "schedule": "daily",
        "start_time": "09:00",
        "desc": "تحليل السوق العقاري — تقرير يومي + إشعار"
    },
    {
        "tn": "Alforaijboard-UpdateLiveDB",
        "command": f'cmd /c "cd /d {PROJECT_DIR} && {PYTHON} update_live_db.py"',
        "schedule": "daily",
        "start_time": "06:00",
        "desc": "تحديث قاعدة البيانات الحية من Supabase (live-db.json)"
    },
    {
        "tn": "Alforaijboard-SystemMonitor",
        "command": f'cmd /c "cd /d {PROJECT_DIR} && {PYTHON} monitor.py"',
        "schedule": "hourly",
        "start_time": "00:00",
        "desc": "مراقبة صحة النظام (API, Supabase, Disk, Cron)"
    },
    {
        "tn": "Alforaijboard-EgressCheck",
        "command": f'cmd /c "cd /d {PROJECT_DIR} && {PYTHON} egress_tracker.py"',
        "schedule": "daily",
        "start_time": "20:00",
        "desc": "مراقبة استهلاك Egress في Supabase — تنبيه قبل الحد"
    },
]


def create_task(task):
    cmd = [
        "schtasks", "/create", "/tn", task["tn"], "/tr", task["command"],
        "/sc", task["schedule"], "/st", task.get("start_time", "00:00"),
        "/f", "/rl", "highest", "/sd", "2026-09-07",
        "/mo", "1" if task["schedule"] == "hourly" else "1",
    ]
    print(f"Creating: {task['tn']}")
    print(f"  Description: {task['desc']}")
    print(f"  Schedule: {task['schedule']} at {task.get('start_time', '00:00')}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"  ✅ Created successfully")
        else:
            print(f"  ⚠️ Failed (exit {result.returncode}):")
            print(f"     {result.stderr[:300]}")
            if "Access is denied" in result.stderr or "access denied" in result.stderr.lower():
                print("     → حاول تشغيل كمسؤول (Run as Administrator)")
    except Exception as e:
        print(f"  ❌ Error: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("إنشاء مهام Windows Task Scheduler للأتمتة الكاملة")
    print("=" * 60)
    print(f"Project dir: {PROJECT_DIR}")
    print(f"Python: {PYTHON}")
    print()

    for task in TASKS:
        create_task(task)

    print()
    print("=" * 60)
    print("اكتمل!")
    print("=" * 60)
    print()
    print("لعرضすべての المهام المُنشأة:")
    print("  schtasks /query /fo LIST | findstr Alforaijboard")
    print()
    print("لحذف مهمة:")
    print('  schtasks /delete /tn "task_name" /f')
    print()
    print("لتشغيل مهمة يدوياً:")
    print('  schtasks /run /tn "task_name"')
