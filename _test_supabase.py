#!/usr/bin/env python
"""Quick test: fetch count + 1 sample from Supabase market_listings."""
import json, os, urllib.request, ssl, sys

PROJECT = "https://bwspcsiazbwrrxpgoldx.supabase.co"
BASE = PROJECT + "/rest/v1"
KEY = os.environ.get("SUPABASE_KEY")
if not KEY:
    raise SystemExit("SUPABASE_KEY environment variable not set. Set it in .env or the hosting environment.")

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def req(path):
    url = BASE + path
    r = urllib.request.Request(url)
    r.add_header("apikey", KEY)
    r.add_header("Authorization", "Bearer " + KEY)
    with urllib.request.urlopen(r, context=ctx, timeout=30) as resp:
        return json.loads(resp.read())

# count
cnt = req("/market_listings?select=count")
print("COUNT:", json.dumps(cnt, indent=2))

# 1 sample  
sample = req("/market_listings?limit=1")
if isinstance(sample, list) and sample:
    print("SAMPLE KEYS:", list(sample[0].keys()))
    print("SAMPLE[0]:", json.dumps(sample[0], indent=2, ensure_ascii=False)[:2000])
else:
    print("SAMPLE:", json.dumps(sample, indent=2))
