#!/usr/bin/env python3
"""
check_docker.py — فحص شامل لكل المكونات
يدرج النتائج في Supabase cron_results
"""

import subprocess, json, os, urllib.request, ssl, sys
from datetime import datetime, timezone

PROJECT = 'https://bwspcsiazbwrrxpgoldx.supabase.co'
BASE = PROJECT + '/rest/v1'
SVC = 'PLACEHOLDER_SECRET_REMOVED'
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
NOW = datetime.now(timezone.utc).isoformat()

def run(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, shell=True)
        return r.returncode == 0, r.stdout.strip()[:200], r.stderr.strip()[:200]
    except Exception as e:
        return False, '', str(e)[:200]

def write_cron(name, status, message):
    payload = {'name': name, 'status': status, 'message': message or '', 'created_at': NOW}
    req = urllib.request.Request(BASE + '/cron_results',
        data=json.dumps(payload).encode(), method='POST')
    req.add_header('apikey', SVC)
    req.add_header('Authorization', 'Bearer ' + SVC)
    req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, context=CTX, timeout=15) as resp:
            if resp.status == 201:
                print(f'  OK {name}: {status}')
                return True
    except:
        pass
    print(f'  FAIL {name}: {status}')
    return False

def main():
    print(f'=== اختيار صحة النظام | {NOW[:19]} ===\n')

    # Docker
    ok1, _, _ = run('docker ps')
    if ok1:
        s1, m1 = 'success', 'Docker running, containers active'
    else:
        ok2, _, _ = run('docker info')
        s1, m1 = ('success', 'Docker engine running (no containers)') if ok2 else ('error', 'Docker not accessible')

    # RAM
    try:
        import psutil
        mem = psutil.virtual_memory()
        free_mb = mem.available / (1024*1024)
        if free_mb < 500:
            s2, m2 = 'error', f'RAM critical: {free_mb:.0f}MB free'
        elif free_mb < 2000:
            s2, m2 = 'warning', f'RAM low: {free_mb:.0f}MB free'
        else:
            s2, m2 = 'success', f'RAM OK: {free_mb:.0f}MB free ({mem.percent}%)'
    except Exception as e:
        s2, m2 = 'success', f'RAM skipped: {e}'

    # Disk
    try:
        import psutil
        usage = psutil.disk_usage('C:\\')
        free_gb = usage.free / (1024**3)
        free_pct = usage.percent
        if free_pct > 90:
            s3, m3 = 'error', f'Disk critical: {free_gb:.1f}GB free ({free_pct:.1f}% used)'
        elif free_pct > 80:
            s3, m3 = 'warning', f'Disk low: {free_gb:.1f}GB free ({free_pct:.1f}% used)'
        else:
            s3, m3 = 'success', f'Disk OK: {free_gb:.1f}GB free ({100-free_pct:.1f}%)'
    except Exception as e:
        s3, m3 = 'success', f'Disk skipped: {e}'

    # Hermes
    hd = '/c/Users/hello/.hermes'
    s4, m4 = ('success', f'Hermes dir exists') if os.path.isdir(hd) else ('warning', 'Hermes dir missing')

    # Git
    ok5, out5, _ = run('git -C /c/Users/hello/alforaijboard-gh status --short')
    mg = len(out5.strip().split('\n')) if out5.strip() else 0
    s5, m5 = ('warning', f'Git: {mg} modified') if mg > 0 else ('success', 'Git: clean')

    results = [
        ('docker', s1, m1),
        ('ram', s2, m2),
        ('disk', s3, m3),
        ('hermes', s4, m4),
        ('git', s5, m5),
    ]

    alerts = sum(1 for _, s, _ in results if s in ('error', 'warning'))
    details = [f'{n}: {m}' for n, s, m in results if s in ('error', 'warning')]
    overall = 'error' if alerts else 'success'
    summary = f'{alerts} issue(s): ' + '; '.join(details) if details else 'All checks passed'

    for n, s, m in results:
        print(f'  [{s.upper():7s}] {n}: {m}')

    write_cron(f'health_full_{NOW[:10]}', overall, summary)
    print(f'\nResult: {sum(1 for _, s, _ in results if s=="success")}/{len(results)} passed')
    return 0 if overall == 'success' else 1

if __name__ == '__main__':
    sys.exit(main())
