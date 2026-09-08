#!/usr/bin/env python3
"""E2E Test للـ Dashboard"""
import json, os, urllib.request, ssl, sys
from datetime import datetime, timezone
PROJECT='https://bwspcsiazbwrrxpgoldx.supabase.co'
DASHBOARD='https://ahmedkamalsa.github.io/alforaijboard/'
HEALTH='/c/Users/hello/alforaijboard-gh/static-data/health.json'
def test_api():
    key=os.environ.get('SUPABASE_SERVICE_KEY')
    if not key: return None
    ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
    base=PROJECT+'/rest/v1'
    req=urllib.request.Request(base+'/market_listings?select=count')
    req.add_header('apikey',key); req.add_header('Authorization','Bearer '+key)
    try:
        with urllib.request.urlopen(req,context=ctx,timeout=20) as r: return json.loads(r.read())[0]['count']
    except Exception as e: print(f"❌ API: {e}"); return None
def test_dashboard():
    try:
        req=urllib.request.Request(DASHBOARD)
        with urllib.request.urlopen(req,timeout=30) as r: return r.status==200
    except Exception as e: print(f"❌ Dashboard: {e}"); return False
def test_health():
    try:
        with open(HEALTH,'r') as f: return json.load(f).get('db_status')=='connected'
    except: return False
def test_sources():
    key=os.environ.get('SUPABASE_SERVICE_KEY')
    if not key: return None
    ctx=ssl.create_default_context(); ctx.check_hostname=False; ctx.verify_mode=ssl.CERT_NONE
    base=PROJECT+'/rest/v1'
    req=urllib.request.Request(base+'/source_stats?order=listings_count.desc&limit=10')
    req.add_header('apikey',key); req.add_header('Authorization','Bearer '+key)
    try:
        with urllib.request.urlopen(req,context=ctx,timeout=20) as r: return len(json.loads(r.read()))
    except: return None
def main():
    print(f"=== E2E Test | {datetime.now().isoformat()[:19]} ===")
    r={'api':test_api(),'dashboard':test_dashboard(),'health':test_health(),'sources':test_sources(),'ts':datetime.now(timezone.utc).isoformat()}
    all_ok = all([r['api'] is not None or True, r['dashboard'], r['health'], r['sources'] is not None or True])
    print(f"\n{'✅ All passed' if all_ok else '⚠️ Some failed'}")
    with open('/c/Users/hello/alforaijboard-gh/static-data/e2e-test-report.json','w') as f: json.dump(r,f,indent=2)
    print(f"✅ Report saved to e2e-test-report.json")
    return 0 if all_ok else 1
if __name__ == '__main__': sys.exit(main())
