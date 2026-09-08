#!/usr/bin/env python3
"""
system_health_check.py — الفحص الكامل لكل الساعة
الفحوصات:
١. Docker daemon running (docker ps)
٢. RAM free > 500MB
٣. Hermes agents processes (alive check)
٤. Disk space on C:/Users/hello (warn <10% free)
٥. Git repo status on alforaijboard (uncommitted changes alert)

النتيجة تُقلّب لملف JSON محلي + تُرسل لـ Supabase cron_results.
"""

import json, os, subprocess, sys, urllib.request, ssl
from datetime import datetime, timezone

PROJECT = os.environ.get('SUPABASE_URL', 'https://bwspcsiazbwrrxpgoldx.supabase.co')
BASE = PROJECT + '/rest/v1'
SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY',
    'PLACEHOLDER_SECRET_REMOVED')
REPO_DIR = os.environ.get('REPO_DIR', 'C:/Users/hello/alforaijboard-gh')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def _ps1(script: str) -> dict:
    """تشغيل سكربت PowerShell وترجع {'stdout','stderr','rc'}."""
    cmd = ['powershell', '-NoProfile', '-Command', script]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return {'stdout': r.stdout.strip(), 'stderr': r.stderr.strip(), 'rc': r.returncode}
    except subprocess.TimeoutExpired:
        return {'stdout': '', 'stderr': 'timeout', 'rc': 124}
    except Exception as e:
        return {'stdout': '', 'stderr': str(e), 'rc': 1}


def write_cron(name, status, message='', duration_ms=None,
               records_affected=None, created_at=None):
    payload = {'name': name, 'status': status, 'message': message or ''}
    if duration_ms is not None:
        payload['duration_ms'] = duration_ms
    if records_affected is not None:
        payload['records_affected'] = records_affected
    if created_at:
        payload['created_at'] = created_at
    data = json.dumps(payload).encode()
    req = urllib.request.Request(BASE + '/cron_results', data=data, method='POST')
    req.add_header('apikey', SERVICE_KEY)
    req.add_header('Authorization', 'Bearer ' + SERVICE_KEY)
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            result = json.loads(resp.read())
            print(f"  ✅ Supabase: {name} -> {status}")
            return True, result
    except urllib.error.HTTPError as e:
        print(f"  ❌ Supabase HTTP {e.code}: {e.read().decode()[:200]}")
        return False, None
    except Exception as e:
        print(f"  ❌ Supabase: {e}")
        return False, None


def check_docker():
    """فحص Docker daemon."""
    r = subprocess.run('docker ps 2>&1', shell=True, capture_output=True,
                       text=True, timeout=15, cwd=REPO_DIR)
    stdout, stderr, code = r.stdout.strip(), r.stderr.strip(), r.returncode
    if code != 0 or 'Cannot connect' in stdout or 'cannot find' in stdout.lower():
        return {
            'status': 'error',
            'message': 'Docker daemon غير متاح — خدمة Docker Desktop ليست نشطة',
            'containers': 0,
        }
    lines = [l for l in stdout.split('\n') if l.strip() and not l.startswith('CONTAINER')]
    if not lines:
        return {
            'status': 'ok',
            'message': 'Docker يعمل لكن لا توجد containers نشطة',
            'containers': 0,
        }
    running = sum(1 for l in lines if 'Up' in l)
    return {
        'status': 'ok',
        'message': f'Docker يعمل — {running} container(s) نشطة',
        'containers': running,
    }


def check_ram():
    """فحص RAM الحرة > 500MB — Win32_OperatingSystem.
    ملاحظة: FreePhysicalMemory و TotalVisibleMemorySize بتاعت Win32 API بتاع Windows
    بيعطي بالـ Kilobytes (KB) مش Bytes كما يشير names.
    عشان ذلك بقسم على 1KB (1024 بايت) عشان نحصل MB."""
    out = _ps1(
        "$os = Get-CimInstance Win32_OperatingSystem;"
        "[PSCustomObject]@{"
        "FreeMB=[math]::Round($os.FreePhysicalMemory/1KB,1);"
        "TotalMB=[math]::Round($os.TotalVisibleMemorySize/1KB,1)"
        "} | ConvertTo-Json"
    )
    if out['rc'] != 0 or not out['stdout']:
        return {
            'status': 'error',
            'message': f'فشل PowerShell: {out["stderr"][:150]}',
            'free_mb': None,
            'total_mb': None,
        }
    try:
        obj = json.loads(out['stdout'])
        free_mb = float(obj.get('FreeMB', 0))
        total_mb = float(obj.get('TotalMB', 0))
    except Exception as e:
        return {
            'status': 'error',
            'message': f'فشل قراءة RAM من PowerShell: {e}',
            'free_mb': None,
            'total_mb': None,
        }

    if free_mb <= 0:
        return {
            'status': 'error',
            'message': 'قيمة RAM الحرة صفر أو سالبة — مؤشر خاطئ',
            'free_mb': free_mb,
            'total_mb': total_mb,
        }

    threshold_mb = 500
    if free_mb < threshold_mb:
        return {
            'status': 'warning',
            'message': f'RAM حرة قليلة: {free_mb:.0f}MB فقط (الحد 500MB)',
            'free_mb': free_mb,
            'total_mb': total_mb,
        }
    free_pct = round(free_mb / total_mb * 100, 1) if total_mb else None
    return {
        'status': 'ok',
        'message': f'RAM حرة كافية: {free_mb:.0f}MB / {total_mb:.0f}MB ({free_pct}%)' if total_mb else f'{free_mb:.0f}MB حرة',
        'free_mb': free_mb,
        'total_mb': total_mb,
    }


def check_agents():
    """قائمة عمليات الوكلاء (python/node/uv) عبر PowerShell."""
    out = _ps1(
        "Get-Process | Where-Object { $_.Name -match 'python|node|uv' } "
        "| Select-Object Id, Name | ConvertTo-Csv -NoTypeInformation"
    )
    agents = []
    if out['rc'] == 0 and out['stdout']:
        for line in out['stdout'].split('\n'):
            line = line.strip()
            if not line or line.startswith('Id,'):
                continue
            parts = line.split(',', 1)
            if len(parts) >= 2:
                try:
                    pid = int(parts[0].strip().strip('"'))
                except ValueError:
                    continue
                name = parts[1].strip().strip('"')
                agents.append({'pid': pid, 'name': name})

    if not agents:
        # bash fallback
        r = subprocess.run("ps aux 2>/dev/null | grep -E 'python|node|uv' | grep -v grep",
                          shell=True, capture_output=True, text=True, timeout=10)
        for line in r.stdout.split('\n'):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 2:
                try:
                    pid = int(parts[1])
                except (ValueError, IndexError):
                    continue
                agents.append({'pid': pid, 'name': parts[0]})

    if not agents:
        return {
            'status': 'warning',
            'message': 'لا توجد عمليات وكلاء/agents قيد التشغيل (python/node/uv)',
            'count': 0,
            'pids': [],
        }
    return {
        'status': 'ok',
        'message': f'{len(agents)} عملية من عمليات الوكلاء/agents شغالة',
        'count': len(agents),
        'pids': agents,
    }


def check_disk():
    """فحص مساحة القرص C: عبر PowerShell (Win32_LogicalDisk)."""
    out = _ps1(
        "Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | "
        "Select-Object DeviceID, Size, FreeSpace | ConvertTo-Json"
    )
    if out['rc'] != 0 or not out['stdout']:
        # bash df fallback
        r = subprocess.run('df -h /c 2>&1 || df -h C: 2>&1',
                          shell=True, capture_output=True, text=True, timeout=10)
        for line in r.stdout.split('\n'):
            if 'C:' in line or '/c' in line:
                parts = line.split()
                if len(parts) >= 4:
                    try:
                        use_pct = int(parts[4].replace('%', ''))
                        free_gb = float(parts[3].replace('G', ''))
                        total_gb = round(free_gb + free_gb * use_pct / (100 - use_pct), 1) if use_pct < 100 else free_gb * 2
                    except (ValueError, IndexError):
                        use_pct, free_gb, total_gb = 0, 0, 0
                    break
        else:
            return {
                'status': 'error',
                'message': 'فشل قياس القرص',
                'free_gb': None,
                'use_percent': None,
            }
        used_gb = round(total_gb - free_gb, 1)
        use_pct = round(used_gb / total_gb * 100, 1) if total_gb > 0 else 0
    else:
        try:
            disks = json.loads(out['stdout'])
            if isinstance(disks, dict):
                disks = [disks]
            c_disk = next((d for d in disks
                           if d.get('DeviceID', '').upper().startswith('C')), None)
            if not c_disk:
                return {
                    'status': 'error',
                    'message': 'لم نعثر على القرص C:',
                    'free_gb': None,
                    'use_percent': None,
                }
            total_gb = round(float(c_disk.get('Size', 0)) / 1e9, 1)
            free_gb = round(float(c_disk.get('FreeSpace', 0)) / 1e9, 1)
            used_gb = round(total_gb - free_gb, 1)
            use_pct = round(used_gb / total_gb * 100, 1) if total_gb > 0 else 0
        except Exception as e:
            return {
                'status': 'error',
                'message': f'فشل قراءة حجم القرص: {e}',
                'free_gb': None,
                'use_percent': None,
            }

    free_percent = round(100 - use_pct, 1)
    if use_pct > 90 or free_gb < 10:
        return {
            'status': 'warning',
            'message': f'مساحة القرص قليلة: {free_gb:.0f}GB حرة ({free_percent}% free)',
            'free_gb': free_gb,
            'total_gb': total_gb,
            'use_percent': use_pct,
            'free_percent': free_percent,
        }
    return {
        'status': 'ok',
        'message': f'مساحة القرص كافية: {free_gb:.1f}GB حرة ({free_percent}% free) من {total_gb:.1f}GB',
        'free_gb': free_gb,
        'total_gb': total_gb,
        'use_percent': use_pct,
        'free_percent': free_percent,
    }


def check_git():
    """فحص الـ Git repo — غير مضاف/معدل؟"""
    r = subprocess.run(f'cd "{REPO_DIR}" && git status --short 2>&1',
                      shell=True, capture_output=True, text=True, timeout=15)
    stdout, stderr, code = r.stdout.strip(), r.stderr.strip(), r.returncode
    if code != 0:
        return {
            'status': 'error',
            'message': f'فشل فحص Git: {stderr[:150]}',
            'changes': [],
        }
    lines = [l.strip() for l in stdout.split('\n') if l.strip()]
    if not lines:
        return {
            'status': 'ok',
            'message': 'الـ Git repo نظيف — لا توجد تغييرات غير ماضية',
            'changes': [],
        }
    changes = []
    for line in lines:
        parts = line.split(None, 1)
        status = parts[0]
        filepath = parts[1] if len(parts) > 1 else ''
        changes.append({'status': status, 'file': filepath})

    return {
        'status': 'warning' if changes else 'ok',
        'message': f'{len(changes)} تغيير(g) غير ماضية في الـ Git' if changes else 'نظيف',
        'changes': changes,
    }


def main():
    now = datetime.now(timezone.utc)
    ts = now.isoformat()
    timestamp_short = now.strftime('%Y%m%d_%H%M')

    print(f"🔍 بدء فحص النظام — {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 60)

    checks = {}
    t0 = datetime.now(timezone.utc)

    checks['docker'] = check_docker()
    print(f"  Docker: {checks['docker']['status']} — {checks['docker']['message']}")
    checks['ram'] = check_ram()
    print(f"  RAM: {checks['ram']['status']} — {checks['ram']['message']}")
    checks['agents'] = check_agents()
    print(f"  Agents: {checks['agents']['status']} — {checks['agents']['message']}")
    checks['disk'] = check_disk()
    print(f"  Disk: {checks['disk']['status']} — {checks['disk']['message']}")
    checks['git'] = check_git()
    print(f"  Git: {checks['git']['status']} — {checks['git']['message']}")

    t1 = datetime.now(timezone.utc)
    duration_ms = int((t1 - t0).total_seconds() * 1000)

    # تقييم الحالة الكلية
    alerts = []
    for key, val in checks.items():
        if val.get('status') in ('error', 'warning'):
            alerts.append(f"{key}: {val['status']} — {val['message'][:80]}")
    overall = 'error' if any(v.get('status') == 'error' for v in checks.values()) else \
              'warning' if alerts else 'success'

    summary_lines = ['كل الفحوصات طبيعية' if overall == 'success' else '']
    if overall != 'success':
        summary_lines = [f"ALERT: {a}" for a in alerts]
    summary = '\n'.join(summary_lines) or 'كل الفحوصات طبيعية'

    result = {
        'timestamp': ts,
        'timestamp_short': timestamp_short,
        'overall_status': overall,
        'summary': summary,
        'duration_ms': duration_ms,
        'checks': checks,
    }

    # 💾 حفظ محلي
    local_dir = os.path.join(REPO_DIR, 'cron_results')
    os.makedirs(local_dir, exist_ok=True)
    local_file = os.path.join(local_dir, f'health_check_{timestamp_short}.json')
    with open(local_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\n💾 محفوظ محلياً: {local_file}")

    # 📡 إرسال لـ Supabase
    print(f"📡 إرسال لـ Supabase: {PROJECT}/rest/v1/cron_results")
    ok, resp = write_cron(
        name=f'health_check_{timestamp_short}',
        status=overall,
        message=summary,
        duration_ms=duration_ms,
        records_affected=len(checks),
        created_at=ts,
    )
    if ok:
        print(f"✅ وُثّقت في قاعدة البيانات")
    else:
        print(f"⚠️ فشل الإرسال لـ Supabase — مُسجّل محلياً فقط")

    print("\n" + "=" * 60)
    print(f"📋 التقرير النهائي: الحالة الكلية = {overall.upper()} ({duration_ms}ms)")
    icon_map = {'ok': '✅', 'warning': '⚠️', 'error': '❌'}
    for k, v in checks.items():
        icon = icon_map.get(v.get('status', 'unknown'), '❓')
        print(f"   {icon} {k}: {v.get('message','')}")

    sys.exit(2 if overall == 'error' else (1 if overall == 'warning' else 0))


if __name__ == '__main__':
    main()
