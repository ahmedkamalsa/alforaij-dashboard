/**
 * live-supabase-client.js
 * عميل Supabase مستقل — يربط dashboard بـ Supabase API مباشرة
 * بدون أي backend server
 *
 * يستخدم Anon Key مباشرة من static-data/live-db.json
 * ويدعم:
 *   - جلب السجلات الكاملة من market_listings (مع pagination)
 *   - جلب الـ 50 development
 *   - جلب سجلات opportunities, clients, alerts, outreach stats
 *   - 헬스 تشك من Supabase (عدد السجلات، آخر تحديث، الحالة)
 *   - تحليل سريع: توزيع المصادر، المعاملات، الأسعار، المحافظات
 */

(function(global) {
'use strict';

// ============================================================================
// الإعدادات من static-data/live-db.json
// ============================================================================
const DB_CONFIG = (function() {
  try {
    const resp = fetch('static-data/live-db.json');
    return resp.then(r => r.json()).catch(() => null);
  } catch { return Promise.resolve(null); }
})();

const FALLBACK_CONFIG = {
  url: 'https://bwspcsiazbwrrxpgoldx.supabase.co',
  anonKey: 'sb_publishable_c84oHQS94osRqw_SiTIqMg_8icxvatZ'
};

// ============================================================================
// utilities
// ============================================================================
function normalizeArabic(str) {
  return String(str || '')
    .replace(/[إأآا]/g, 'ا')
    .replace(/[ىي]/g, 'ي')
    .replace(/[ة]/g, 'ه')
    .replace(/[^ا-يa-zA-Z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();
}

function fetchWithAuth(url, options = {}) {
  return fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'apikey': config?.anonKey,
      'Authorization': `Bearer ${config?.anonKey}`,
      ...options.headers,
    }
  });
}

// ============================================================================
// العميل الرئيسي
// ============================================================================
class SupabaseLiveClient {
  constructor() {
    this.config = null;
    this.lastHealth = null;
    this.recordsCache = null;
    this.recordsCacheTime = null;
    this.totalCount = 0;
  }

  async init() {
    const cfg = await DB_CONFIG;
    this.config = cfg || FALLBACK_CONFIG;
    return this.checkConnection();
  }

  get baseUrl() {
    return `${this.config.url}/rest/v1`;
  }

  // ----------------------------------------------------------------
  // الاتصال والتحقق
  // ----------------------------------------------------------------
  async checkConnection() {
    try {
      const url = `${this.baseUrl}/market_listings?select=count`;
      const resp = await fetchWithAuth(url);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      const count = data?.count || (Array.isArray(data) ? data.length : 0);
      this.totalCount = count;
      this.lastHealth = {
        status: 'connected',
        source: 'live_supabase',
        total_records: count,
        checked_at: new Date().toISOString(),
        url: this.config.url,
      };
      return this.lastHealth;
    } catch (err) {
      this.lastHealth = {
        status: 'disconnected',
        source: 'live_supabase',
        error: err.message,
        checked_at: new Date().toISOString(),
      };
      return this.lastHealth;
    }
  }

  // ----------------------------------------------------------------
  // جلب السجلات — مع pagination كاملة
  // ----------------------------------------------------------------
  async fetchAllListings(options = {}) {
    const { limit = 1000, page = 0, filters = {} } = options;
    const records = [];
    let offset = page * limit;

    while (true) {
      const params = new URLSearchParams();
      params.set('limit', String(limit));
      params.set('offset', String(offset));
      if (filters.source) params.set('source', filters.source);
      if (filters.transaction) params.append('transaction', filters.transaction);
      if (filters.governorate) params.set('governorate', filters.governorate);

      const url = `${this.baseUrl}/market_listings?${params.toString()}`;
      const resp = await fetchWithAuth(url);
      if (!resp.ok) throw new Error(`HTTP ${resp.status} at offset ${offset}`);

      const data = await resp.json();
      const rows = Array.isArray(data) ? data : [];
      if (!rows.length) break;

      records.push(...rows);
      offset += limit;
      if (rows.length < limit) break;
    }

    this.recordsCache = records;
    this.recordsCacheTime = new Date().toISOString();
    return records;
  }

  async getListingsCount() {
    if (this.totalCount > 0) return this.totalCount;
    const health = await this.checkConnection();
    return health.total_records || 0;
  }

  // ----------------------------------------------------------------
  // التطويرات
  // ----------------------------------------------------------------
  async fetchAllDevelopments() {
    const url = `${this.baseUrl}/market_developments?select=*&orderby=id.desc&limit=100`;
    const resp = await fetchWithAuth(url);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    return await resp.json();
  }

  // ----------------------------------------------------------------
  // فرص المكسب
  // ----------------------------------------------------------------
  async fetchOpportunities() {
    const url = `${this.baseUrl}/opportunities?select=*&orderby=created_at.desc&limit=500`;
    const resp = await fetchWithAuth(url);
    if (!resp.ok) {
      // قد لا يكون الجدول متاحاً للقراءة العامة — نرجع null
      return null;
    }
    return await resp.json();
  }

  // ----------------------------------------------------------------
  // تحليل سريع للبيانات
  // ----------------------------------------------------------------
  analyzeListings(records) {
    if (!records?.length) return { total: 0 };

    const sources = {};
    const transactions = {};
    const governorates = {};
    const priceDisclosed = 0;
    const priceTotal = 0;
    const maxPrice = { value: 0 };
    const minPrice = { value: Infinity };
    const prices = [];
    const areas = new Set();

    for (const row of records) {
      const src = row.source || row.source_name || 'غير معروف';
      sources[src] = (sources[src] || 0) + 1;

      const tx = row.transaction || 'غير معروف';
      transactions[tx] = (transactions[tx] || 0) + 1;

      const gov = row.governorate || row.gov || 'غير محدد';
      governorates[gov] = (governorates[gov] || 0) + 1;

      const area = row.area || row.area_name || '';
      if (area) areas.add(area);

      const price = Number(row.price);
      if (price > 0) {
        prices.push(price);
        priceTotal += price;
        if (price > maxPrice.value) maxPrice.value = price;
        if (price < minPrice.value) minPrice.value = price;
      }
    }

    const sortedSources = Object.entries(sources)
      .sort((a, b) => b[1] - a[1])
      .map(([name, count]) => ({ name, count, percentage: Math.round(count / records.length * 100) }));

    const avgPrice = prices.length ? Math.round(priceTotal / prices.length) : 0;
    const medianPrice = prices.length ? prices.sort((a,b) => a-b)[Math.floor(prices.length/2)] : 0;

    return {
      total: records.length,
      sources: sortedSources,
      transactions: Object.entries(transactions)
        .sort((a, b) => b[1] - a[1])
        .map(([name, count]) => ({ name, count, percentage: Math.round(count / records.length * 100) })),
      governates: Object.entries(governorates)
        .sort((a, b) => b[1] - a[1])
        .map(([name, count]) => ({ name, count })),
      price_disclosed: prices.length,
      price_undisclosed: records.length - prices.length,
      price_disclosure_rate: Math.round(prices.length / records.length * 100),
      average_price: avgPrice,
      median_price: medianPrice,
      max_price: maxPrice.value < Infinity ? maxPrice.value : 0,
      min_price: minPrice.value < Infinity ? minPrice.value : 0,
      areas_count: areas.size,
      analysis_time: new Date().toISOString(),
    };
  }
}

// ============================================================================
// Export
// ============================================================================
const supabaseLive = new SupabaseLiveClient();
global.supabaseLive = supabaseLive;
global.SupabaseLiveClient = SupabaseLiveClient;

})(typeof window !== 'undefined' ? window : typeof globalThis !== 'undefined' ? globalThis : this);
