#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
sync_live_db.py — يملochem بيانات market_listings من Supabase وينقذها لـ dashboard المباشر.

كل 30 دقيقة HELLO بنركّب السكربت ويحفّز:
  1. جلب كل الـ records من market_listings (pagination تلقائي).
  2. حفظها في site/static-data/live-db.json圧縮 JSON مضغوط (minified).
  3. تحديث site/last-updated.json بالـ timestamp والعدد.
"""

import json, os, ssl, sys, time, urllib.request, urllib.parse, datetime

PROJECT = "https://bwspcsiazbwrrxpgoldx.supabase.co"
BASE = PROJECT + "/rest/v1"
KEY = os.environ.get("SUPABASE_KEY")
if not KEY:
    raise SystemExit("SUPABASE_KEY environment variable not set. Set it in .env or the hosting environment.")

PROJECT_DIR = os.environ.get(
    "ALFORAIJBOARD_DIR",
    r"C:\Users\hello\alforaijboard-gh",
)
STATIC_DIR = os.path.join(PROJECT_DIR, "site", "static-data")
SITE_DIR   = os.path.join(PROJECT_DIR, "site")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(SITE_DIR, exist_ok=True)

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def req(path, params=None, method="GET", body=None):
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params, safe="[],")
    r = urllib.request.Request(url, method=method)
    r.add_header("apikey", KEY)
    r.add_header("Authorization", "Bearer " + KEY)
    r.add_header("Content-Type", "application/json")
    if body:
        r.data = json.dumps(body).encode()
    try:
        with urllib.request.urlopen(r, context=ctx, timeout=120) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else []
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:500]
        return {"error": e.code, "body": body}
    except Exception as e:
        return {"error": str(e)[:300]}

def get_total():
    """Get total count of market_listings."""
    res = req("/market_listings?select=count")
    if isinstance(res, list) and res:
        return res[0].get("count", 0)
    if isinstance(res, dict):
        return res.get("count") or 0
    return 0

def fetch_all(limit=1000):
    """Fetch all market_listings with pagination."""
    total = get_total()
    print(f"  إجمالي السجلات في قاعدة البيانات: {total}")
    if total == 0:
        print("  ⚠️  لا توجد سجلات — نرجع قائمة فاضية")
        return []

    all_records = []
    page = 0
    errors = 0
    t0 = time.time()

    while True:
        start = page * limit
        if start >= total:
            break

        res = req(
            "/market_listings",
            params={
                "limit": limit,
                "offset": start,
                "order": "id.asc",
            },
        )

        if isinstance(res, dict) and "error" in res:
            print(f"  ⚠️  خطأ في الصفحة {page + 1}: HTTP {res['error']} — {res.get('body','')[:80]}")
            errors += 1
            if errors > 5:
                print("  ⛔大量 errors - نوقف السحب")
                break
            page += 1
            continue

        if not isinstance(res, list) or not res:
            if isinstance(res, dict):
                print(f"  ⚠️  رد غير متوقع من الصفحة {page + 1}: {list(res.keys())}")
            break

        all_records.extend(res)
        print(f"  📄 صفحة {page + 1}: +{len(res)} سجل (المجموع: {len(all_records)} / {total})")

        if len(res) < limit:
            break
        page += 1

        if page % 5 == 0:
            elapsed = time.time() - t0
            rate = len(all_records) / elapsed if elapsed > 0 else 0
            print(f"     ... {len(all_records)} حتى الآن من {total} (معدل: {rate:.1f} سجل/ثانية) ...")

    elapsed = time.time() - t0
    print(f"  ✅ اكتمل السحب: {len(all_records)} سجل في {elapsed:.1f} ثانية")
    return all_records

def save_live_db(records):
    """حفظ الـ records في site/static-data/live-db.json (مضغوط)."""
    path = os.path.join(STATIC_DIR, "live-db.json")
    payload = {
        "fetched_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "record_count": len(records),
        "project_url": PROJECT,
        "data": records,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, separators=(",", ":"))
    size_kb = os.path.getsize(path) / 1024
    print(f"  ✅ live-db.json محفوظ: {len(records)} سجل  |  حجم الملف: {size_kb:.1f} KB")
    return path

def save_last_updated(record_count):
    """تحديث site/last-updated.json."""
    now = datetime.datetime.now(datetime.timezone.utc)
    path = os.path.join(SITE_DIR, "last-updated.json")
    payload = {
        "generated_at": now.isoformat(),
        "last_synced": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "record_count": record_count,
        "source": "supabase_market_listings",
        "project": PROJECT,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"  ✅ last-updated.json محدث: {record_count} سجل | {now.strftime('%Y-%m-%d %H:%M:%S')} UTC")

def main():
    print("=" * 60)
    print("  sync_live_db.py — Synching Supabase → Live Dashboard")
    print("=" * 60)
    print(f"  المشروع: {PROJECT}")
    print(f"  الجداول: market_listings")
    print(f"  الوجهة: site/static-data/live-db.json")
    print(f"  الوقت: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("-" * 60)

    # جلب البيانات
    print("\n🔄 جلب البيانات من Supabase...")
    records = fetch_all(limit=1000)

    if not records:
        print("\n⛔ لا يوجد بيانات تم جلبها. التأكد من:")
        print("   - المفتاح صحيح وعضو RLS")
        print("   - الجدول market_listings موجود وشفاف")
        sys.exit(1)

    # حفظ الملفات
    print("\n💾 حفظ الملفات...")
    save_live_db(records)
    save_last_updated(len(records))

    print("\n" + "=" * 60)
    print(f"  ✅ Sync اكتمل! {len(records):,} سجل من Market Listings")
    print(f"  الوجهة: site/static-data/live-db.json")
    print(f"  last-updated.json محدث")
    print("=" * 60)

if __name__ == "__main__":
    main()
