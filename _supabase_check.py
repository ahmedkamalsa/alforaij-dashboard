import json, os, urllib.request, ssl

PROJECT = 'https://bwspcsiazbwrrxpgoldx.supabase.co'
BASE = PROJECT + '/rest/v1'
SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY',
    'PLACEHOLDER_SECRET_REMOVED')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

# GET existing row
req = urllib.request.Request(BASE + '/cron_results?limit=1')
req.add_header('apikey', SERVICE_KEY)
req.add_header('Authorization', 'Bearer ' + SERVICE_KEY)
with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
    data = json.loads(resp.read())
    print('Existing row:')
    print(json.dumps(data, ensure_ascii=False, indent=2))

# Now POST with same structure
payload = {
    'name': 'system_health_cron',
    'status': 'ok_with_warnings',
    'message': 'RAM ok | Docker down | Hermes agents ok | Disk 14.8% free | Git has uncommitted changes | Supabase log uploaded',
    'created_at': '2026-09-08T13:01:45+03:00',
}
data = json.dumps(payload).encode()
req2 = urllib.request.Request(BASE + '/cron_results', data=data, method='POST')
req2.add_header('apikey', SERVICE_KEY)
req2.add_header('Authorization', 'Bearer ' + SERVICE_KEY)
req2.add_header('Content-Type', 'application/json')
try:
    with urllib.request.urlopen(req2, context=ctx, timeout=10) as resp:
        result = json.loads(resp.read())
        print('\nPOST OK')
        print(json.dumps(result, ensure_ascii=False, indent=2)[:500])
except urllib.error.HTTPError as e:
    print(f'\nPOST failed: HTTP {e.code} — {e.read().decode()[:300]}')
