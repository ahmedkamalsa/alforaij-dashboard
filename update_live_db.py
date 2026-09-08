#!/usr/bin/env python3
"""تحديث ملف live-db.json بالبيانات الحية من Supabase"""
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
    r.add_header('Content-Type','application/json')
    with urllib.request.urlopen(r, context=ctx, timeout=30) as resp: return json.loads(resp.read())
def main():
    now = datetime.now(timezone.utc).isoformat()
    listings = get('/market_listings?order=id.desc&limit=1000')
    print(f"الإعلانات المحمّلة: {len(listings)}")
    summary = get('/market_listings?select=count')
    total = summary[0]['count'] if summary else 0
    print(f"الإجمالي: {total}")
    prices = [l.get('price',0) for l in listings if l.get('price')]
    avg = round(sum(prices)/len(prices)) if prices else 0
    data = {'fetched_at':now,'record_count':len(listings),'project_url':PROJECT,'total_count':total,
            'summary':{'average_price':avg,'min_price':min(prices) if prices else 0,'max_price':max(prices) if prices else 0,'top_areas':[]},
            'data':listings[:100]}
    path = '/c/Users/hello/alforaijboard-gh/site/static-data/live-db.json'
    with open(path,'w',encoding='utf-8') as f: json.dump(data,f,indent=2,ensure_ascii=False)
    print(f"✅ محفوظ: {path}")
    os.chdir('/c/Users/hello/alforaijboard-gh')
    os.system(f'git add {path}')
    print("✅ مُضاف للـ git")
if __name__ == '__main__': main()
