#!/usr/bin/env python3
"""Fetch ALL 3,376 real listings from Supabase bwspcsiazbwrrxpgoldx."""

import json, ssl, os, urllib.request, urllib.parse

PROJECT = "https://bwspcsiazbwrrxpgoldx.supabase.co"
BASE = PROJECT + "/rest/v1"

KEYS = [
    os.environ.get("SUPABASE_PUBLISHABLE_KEY"),
    os.environ.get("SUPABASE_SECRET_KEY"),
]
if not all(KEYS):
    raise SystemExit("SUPABASE_PUBLISHABLE_KEY and SUPABASE_SECRET_KEY environment variables not set. Set them in .env or the hosting environment.")

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def req(path, params=None, key=None, method="GET", body=None):
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params, safe="[],")
    r = urllib.request.Request(url, method=method)
    k = key or KEYS[0]
    r.add_header("apikey", k)
    r.add_header("Authorization", "Bearer " + k)
    r.add_header("Content-Type", "application/json")
    if body:
        r.data = json.dumps(body).encode()
    try:
        with urllib.request.urlopen(r, context=ctx, timeout=90) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else []
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode()[:500]
        except:
            body = str(e)
        return {"error": e.code, "body": body}
    except Exception as e:
        return {"error": str(e)[:300]}

def get_count(key):
    """Get total count from Supabase REST API."""
    res = req("/market_listings?select=count", key=key)
    if isinstance(res, list):
        return res[0].get("count") if res else 0
    if isinstance(res, dict):
        return res.get("count") or 0
    return None

def test_key(key):
    """Test if a key works by fetching a small sample."""
    res = req("/market_listings?limit=1", key=key)
    return isinstance(res, list) and len(res) > 0

def fetch_all(key, limit=1000):
    """Fetch all records from market_listings with pagination."""
    # Get total count first
    cnt_res = req("/market_listings?select=count", key=key)
    if isinstance(cnt_res, dict):
        total = cnt_res.get("count", 0)
    elif isinstance(cnt_res, list) and cnt_res:
        total = cnt_res[0].get("count", 0) if cnt_res else 0
    else:
        total = 0
    print(f"  إجمالي من API: {total} إعلان")
    
    all_data = []
    page = 0
    errors = 0
    
    while True:
        start = page * limit
        if start >= total:
            break
        
        res = req("/market_listings?limit=" + str(limit) + 
                  "&offset=" + str(start) + "&order=id.asc", key=key)
        
        if isinstance(res, dict) and "error" in res:
            print(f"  ⚠️ خطأ في الصفحة {page+1}: HTTP {res.get('error')}")
            errors += 1
            if errors > 3:
                print(f"  ⛔太多 errors، نوقف")
                break
            page += 1
            continue
        
        if not res:
            print(f"  ⓘ لا توجد بيانات أكثر старт من offset {start}")
            break
        
        batch = res if isinstance(res, list) else [res]
        all_data.extend(batch)
        print(f"  📄 صفحة {page+1}: +{len(batch)} إعلان (المجموع: {len(all_data)})")
        
        if len(batch) < limit:
            break
        page += 1
        
        if page % 5 == 0:
            print(f"     ... {len(all_data)} حتى الآن (من {total}) ...")
    
    return all_data

def main():
    print("=" * 70)
    print("  Supabase Data Fetch — حصة البيانات الحقيقية")
    print("=" * 70)
    
    # اختبار كل الـ keys
    print("\n--- اختبار المفاتيح ---")
    working_keys = []
    for key in KEYS:
        if test_key(key):
            cnt = get_count(key)
            print(f"  ✅ المفتاح شغال | العدد: {cnt} | المفتاح: ...{key[-15:]}")
            working_keys.append((key, cnt))
        else:
            print(f"  ❌ المفتاح فشل | المفتاح: ...{key[-15:]}")
    
    if not working_keys:
        print("\n⛔ لا يوجد مفتاح شغال! حاول:")
        print("   ١. تفقد الـ keys في Supabase dashboard")
        print("   ٢. 복사 fresh keys من https://bwspcsiazbwrrxpgoldx.supabase.co/settings/api")
        return
    
    # نستخدم أفضل مفتاح (اللي وصل أعلى عدد)
    best_key, total_est = working_keys[0]
    if len(working_keys) > 1 and working_keys[1][1] > working_keys[0][1]:
        best_key, total_est = working_keys[1]
    
    print(f"\n✅ نستخدم المفتاح: ...{best_key[-15:]}")
    
    # جلب كل البيانات
    print("\n--- جلب جميع الإعلانات ---")
    all_listings = fetch_all(best_key, limit=1000)
    
    print(f"\n{'='*70}")
    print(f"  إجمالي الإعلانات: {len(all_listings)}")
    print(f"{'='*70}")
    
    # جلب market_developments
    print("\n--- جلب market_developments ---")
    devs = req("/market_developments?limit=100", key=best_key)
    devs = devs if isinstance(devs, list) else []
    print(f"  market_developments: {len(devs)} تطوير")
    
    # جلب sources table
    print("\n--- جلب sources table ---")
    sources = req("/sources?limit=100", key=best_key)
    sources = sources if isinstance(sources, list) else []
    if sources:
        print(f"  sources table: {len(sources)} مصدر")
        for s in sources:
            print(f"    - {s.get('name')}: access={s.get('access_level')}, phone={s.get('phone_number')}, reliability={s.get('reliability')}")
    else:
        print("  ⚠️ sources table غير موجودة")
    
    # ANALYSIS
    if all_listings:
        print("\n" + "=" * 70)
        print("  🔍 تحليل البيانات الحقيقية من Supabase")
        print("=" * 70)
        
        sources_dist = {}
        types_dist = {}
        cities_dist = {}
        gov_dist = {}
        price_disclosed = 0
        total_price = 0.0
        max_price = 0.0
        min_price = float('inf')
        has_gov = 0
        has_area = 0
        has_price = 0
        areas_all = set()
        
        for ad in all_listings:
            # Source
            src = str(ad.get('source') or '').strip()
            if not src: src = '(empty)'
            sources_dist[src] = sources_dist.get(src, 0) + 1
            
            # Transaction type
            t = str(ad.get('transaction') or '').strip()
            if not t: t = '(empty)'
            types_dist[t] = types_dist.get(t, 0) + 1
            
            # City
            city = str(ad.get('city') or ad.get('area') or '').strip()
            if city:
                cities_dist[city] = cities_dist.get(city, 0) + 1
                areas_all.add(city)
            
            # Governorate
            gov = str(ad.get('governorate') or '').strip()
            if gov:
                gov_dist[gov] = gov_dist.get(gov, 0) + 1
                has_gov += 1
            else:
                pass
            
            # Area
            area = str(ad.get('area') or '').strip()
            if area:
                has_area += 1
                areas_all.add(area)
            
            # Price
            p = ad.get('price')
            if p:
                try:
                    p = float(p)
                    has_price += 1
                    price_disclosed += 1
                    total_price += p
                    if p > max_price: max_price = p
                    if p < min_price: min_price = p
                except:
                    pass
        
        print(f"\n📊 إجمالي الإعلانات: {len(all_listings):,}")
        print(f"🏷️ مصادر فريدة: {len(sources_dist)}")
        print(f"🏙️ مناطق/مدن فريدة: {len(areas_all)}")
        print(f"🏛️ حوكميات معلنة: {has_gov} ({100*has_gov/len(all_listings):.1f}%)")
        print(f"📍 مناطق (area) معلنة: {has_area} ({100*has_area/len(all_listings):.1f}%)")
        print(f"💰 أسعار معلنة: {has_price} ({100*has_price/len(all_listings):.1f}%)")
        
        if has_price > 0:
            print(f"\n💰 التحليل السعري (#{has_price} إعلانات بسعر):")
            print(f"   المتوسط: {total_price/max(has_price,1):,.0f} KD")
            print(f"   الأعلى:   {max_price:,.0f} KD")
            print(f"   الأدنى:   {min_price:,.0f} KD")
            print(f"   المجموع:  {total_price:,.0f} KD")
        
        # TOP SOURCES
        print(f"\n{'='*50}")
        print("  🏢 ترتيب المصادر (الأعلى ← الأدنى)")
        print(f"{'='*50}")
        sorted_sources = sorted(sources_dist.items(), key=lambda x: -x[1])
        top_src = sorted_sources[0][1] if sorted_sources else 1
        
        print(f"  {'المصدر':<35} {'العدد':>6} {'النسبة':>8} {'Bar'}")
        print(f"  {'-'*35} {'-'*6} {'-'*8} {'-'*30}")
        for src, cnt in sorted_sources:
            pct = 100*cnt/len(all_listings)
            bar = "█" * max(1, int(40*cnt/top_src))
            print(f"  {src:<35} {cnt:>6} {pct:>7.1f}% {bar}")
        
        # TOP TRANSACTION TYPES
        print(f"\n{'='*50}")
        print("  📋 أنواع المعاملات")
        print(f"{'='*50}")
        for t, cnt in sorted(types_dist.items(), key=lambda x: -x[1]):
            pct = 100*cnt/len(all_listings)
            print(f"  {t:<35} {cnt:>6} {pct:>7.1f}%")
        
        # TOP CITIES / AREAS
        print(f"\n{'='*50}")
        print(f"  🏙️ أبرز 15 منطقة/مدينة (بعدد الإعلانات)")
        print(f"{'='*50}")
        sorted_areas = sorted(cities_dist.items(), key=lambda x: -x[1])[:15]
        for area, cnt in sorted_areas:
            pct = 100*cnt/len(all_listings)
            print(f"  {area:<35} {cnt:>6} {pct:>7.1f}%")
        
        # GOVERNORATES
        print(f"\n{'='*50}")
        print(f"  🏛️ الحوكميات (التي معلنة في البيانات)")
        print(f"{'='*50}")
        for gov, cnt in sorted(gov_dist.items(), key=lambda x: -x[1]):
            pct = 100*cnt/len(all_listings)
            print(f"  {gov:<35} {cnt:>6} {pct:>7.1f}%")
        
        # TOP high-value listings
        print(f"\n{'='*50}")
        print(f"  💎 أعلى 10 إعلانات بالسعر")
        print(f"{'='*50}")
        price_ads = [(ad, float(ad.get('price', 0))) for ad in all_listings if ad.get('price')]
        price_ads.sort(key=lambda x: -x[1])
        for ad, p in price_ads[:10]:
            src = ad.get('source', '؟')
            area = ad.get('area', ad.get('city', '؟'))
            print(f"  {p:>12,.0f} KD  |  {ad.get('id')}  |  {src:<20} |  {area}")
        
        # TOP high-view listings
        print(f"\n{'='*50}")
        print(f"  👁️ أعلى 10 إعلانات بالمشاهدات")
        print(f"{'='*50}")
        view_ads = [(ad, ad.get('views', 0) or 0) for ad in all_listings]
        view_ads.sort(key=lambda x: -x[1])
        for ad, v in view_ads[:10]:
            src = ad.get('source', '؟')
            area = ad.get('area', ad.get('city', '؟'))
            print(f"  {v:>5} views  |  #{ad.get('id')}  |  {src:<20} |  {area}")
    
    # SAVE DATA
    print("\n" + "=" * 70)
    print("  💾 حفظ البيانات إلى ملفات")
    print("=" * 70)
    
    os.makedirs("supabase_data", exist_ok=True)
    
    with open("supabase_data/market_listings.json", "w", encoding="utf-8") as f:
        json.dump(all_listings, f, ensure_ascii=False, indent=2)
    print(f"  ✅ market_listings.json: {len(all_listings):,} إعلان")
    
    with open("supabase_data/market_developments.json", "w", encoding="utf-8") as f:
        json.dump(devs, f, ensure_ascii=False, indent=2)
    print(f"  ✅ market_developments.json: {len(devs)} تطوير")
    
    with open("supabase_data/sources.json", "w", encoding="utf-8") as f:
        json.dump(sources, f, ensure_ascii=False, indent=2)
    print(f"  ✅ sources.json: {len(sources)} مصدر")
    
    # Save full analysis
    analysis = {
        "total_listings": len(all_listings),
        "sources_count": len(sources_dist),
        "areas_count": len(areas_all),
        "governorates_with_data": has_gov,
        "areas_with_data": has_area,
        "price_disclosed_count": has_price,
        "price_disclosed_pct": round(100*has_price/len(all_listings), 1) if all_listings else 0,
        "avg_price": round(total_price/max(has_price,1), 0),
        "max_price": max_price,
        "min_price": min_price if min_price < float('inf') else 0,
        "total_price_sum": total_price,
        "fetched_at": str(__import__('datetime').datetime.now()),
        "sources_distribution": sources_dist,
        "types_distribution": types_dist,
        "cities_distribution": cities_dist,
        "governorates_distribution": gov_dist,
    }
    
    with open("supabase_data/analysis.json", "w", encoding="utf-8") as f:
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    print(f"  ✅ analysis.json: تحليل كامل")
    
    print(f"\n{'='*70}")
    print(f"  ✅ اكتمل! كل البيانات محفوظة في supabase_data/")
    print(f"{'='*70}")

if __name__ == "__main__":
    main()
