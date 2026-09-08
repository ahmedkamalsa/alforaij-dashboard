#!/usr/bin/env python3
"""تحديث إحصائيات المصادر في جدول source_stats"""
import json, os, urllib.request, ssl
from datetime import datetime, timezone
PROJECT = os.environ.get('SUPABASE_URL', 'https://bwspcsiazbwrrxpgoldx.supabase.co')
BASE = PROJECT + '/rest/v1'
SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
if not SERVICE_KEY:
    print("ERROR: SUPABASE_SERVICE_KEY not set")
    exit(1)
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
def get(p):
    r = urllib.request.Request(BASE + p, method='GET')
    r.add_header('apikey', SERVICE_KEY)
    r.add_header('Authorization', 'Bearer ' + SERVICE_KEY)
    r.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(r, context=ctx, timeout=20) as resp:
        return json.loads(resp.read())
def post(p, d):
    r = urllib.request.Request(BASE + p, data=json.dumps(d).encode(), method='POST')
    r.add_header('apikey', SERVICE_KEY)
    r.add_header('Authorization', 'Bearer ' + SERVICE_KEY)
    r.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(r, context=ctx, timeout=15) as resp:
        return json.loads(resp.read())
def delete(p):
    r = urllib.request.Request(BASE + p, method='DELETE')
    r.add_header('apikey', SERVICE_KEY)
    r.add_header('Authorization', 'Bearer ' + SERVICE_KEY)
    r.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(r, context=ctx, timeout=15) as resp:
        return resp.status
def main():
    now = datetime.now(timezone.utc).isoformat()
    sources = get('/sources?order=name.asc')
    print(f"المصادر: {len(sources)}")
    existing = get('/source_stats?select=id')
    for row in existing: delete(f'/source_stats?id=eq.{row["id"]}')
    print(f"حذف {len(existing)} قديمة")
    for src in sources:
        count = get(f'/market_listings?select=count&source=eq."{src["name"]}"')[0]['count']
        post('/source_stats', {'source_id':src['id'],'listings_count':count,'last_checked':now,'reliability':src.get('reliability',1),'error_count':0})
        print(f"  {src['name'][:30]:30s} → {count} إعلان")
    print(f"\n✅ Updated {len(sources)} sources")
if __name__ == '__main__': main()
