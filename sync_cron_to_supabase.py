#!/usr/bin/env python3
"""
sync_cron_to_supabase.py — مزامنة ملفات cron_results المحلية مع Supabase
"""

import json, os, urllib.request, ssl
from datetime import datetime, timezone

PROJECT = 'https://bwspcsiazbwrrxpgoldx.supabase.co'
BASE = PROJECT + '/rest/v1'
SERVICE_KEY = 'PLACEHOLDER_SECRET_REMOVED'

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def write_cron(name, status, message='', duration_ms=None, created_at=None):
    payload = {'name': name, 'status': status, 'message': message or ''}
    if duration_ms is not None:
        payload['duration_ms'] = duration_ms
    if created_at:
        payload['created_at'] = created_at

    data = json.dumps(payload).encode()
    req = urllib.request.Request(BASE + '/cron_results', data=data, method='POST')
    req.add_header('apikey', SERVICE_KEY)
    req.add_header('Authorization', 'Bearer ' + SERVICE_KEY)
    req.add_header('Content-Type', 'application/json')

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            if resp.status == 201:
                print(f"  OK {name}: {status}")
                return True
            else:
                print(f"  WARN {name}: status={resp.status}")
                return False
    except urllib.error.HTTPError as e:
        print(f"  FAIL {name}: HTTP {e.code}")
        return False
    except Exception as e:
        print(f"  FAIL {name}: {e}")
        return False

def extract_ts(data):
    for k in ['timestamp', 'check_time', 'check_time_utc', 'timestamp_kt', 'check_time_kuwait', 'timestamp_short']:
        v = data.get(k)
        if v and isinstance(v, str):
            return v
    return None

def parse_file(fpath):
    with open(fpath, 'rb') as f:
        text = f.read().decode('utf-8-sig')
    data = json.loads(text)

    ts = extract_ts(data)
    if ts:
        try:
            dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            created_at = dt.isoformat()
            name = 'health_check_' + dt.strftime('%Y%m%d_%H%M')
        except:
            created_at = datetime.now(timezone.utc).isoformat()
            name = os.path.basename(fpath).replace('.json', '')
    else:
        created_at = datetime.now(timezone.utc).isoformat()
        name = os.path.basename(fpath).replace('.json', '')

    # تقييم الحالة
    checks = data.get('checks', {})
    flat = {k: v for k, v in data.items() if isinstance(v, dict) and ('status' in v or 'alert' in v or 'health' in v)}
    if not checks:
        checks = flat

    alert_count = 0
    details = []
    for k, v in checks.items():
        if isinstance(v, dict):
            if v.get('alert'):
                alert_count += 1
            s = v.get('status', '')
            if s in ('stopped', 'error', 'unhealthy'):
                alert_count += 1
                details.append(f"{k}: {s}")

    overall = str(data.get('overall_status', '') or '').lower()
    summary = data.get('summary', '') or data.get('overall_summary', '') or ''
    unreachable = data.get('supabase_status') == 'unreachable'

    if overall == 'error' or alert_count > 0 or unreachable:
        status = 'error'
        msg = summary[:300] if summary else ('; '.join(details) if details else 'error in checks')
    else:
        status = 'success'
        msg = summary[:300] if summary else 'all checks OK'

    return {
        'name': name,
        'status': status,
        'message': msg,
        'duration_ms': data.get('duration_ms'),
        'created_at': created_at,
    }

def sync(local_dir, limit=None):
    if not os.path.isdir(local_dir):
        print(f"ERROR: {local_dir} not found")
        sys.exit(1)

    files = sorted([f for f in os.listdir(local_dir) if f.endswith('.json')])
    if not files:
        print(f"INFO: {local_dir} is empty")
        return 0

    if limit:
        files = files[:limit]

    total = len(files)
    print(f"Found {total} files in {local_dir}")
    ok = 0
    for fname in files:
        fpath = os.path.join(local_dir, fname)
        try:
            cron = parse_file(fpath)
            if write_cron(**cron):
                ok += 1
                synced = fpath + '.synced'
                if not os.path.exists(synced):
                    os.rename(fpath, synced)
        except json.JSONDecodeError as e:
            print(f"SKIP {fname}: bad JSON - {e}")
        except Exception as e:
            print(f"SKIP {fname}: {e}")

    print(f"\nResult: {ok} synced / {total} total")
    return ok

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', default='cron_results')
    ap.add_argument('--limit', type=int, default=None)
    args = ap.parse_args()
    sync(args.dir, limit=args.limit)
