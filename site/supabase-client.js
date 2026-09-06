/**
 * supabase-client.js
 * عميل Supabase متقدم — يربط dashboard بالبيانات الحية من API
 * يدعم: جلب السجلات، التحليل، التقييم، التوصيات
 */

const SUPABASE_URL = 'https://bwspcsiazbwrrxpgoldx.supabase.co';
const ANON_KEY = 'sb_publishable_c84oHQS94osRqw_SiTIqMg_8icxvatZ';

class SupabaseLiveClient {
  constructor() {
    this.cache = new Map();
    this.cacheTimestamps = new Map();
    this.cacheTTL = 5 * 60 * 1000; // 5 دقائق
  }

  async fetch(url, options = {}) {
    const headers = {
      'Content-Type': 'application/json',
      'apikey': ANON_KEY,
      'Authorization': `Bearer ${ANON_KEY}`,
      ...options.headers,
    };
    
    try {
      const response = await fetch(url, {
        ...options,
        headers,
        cache: 'no-store',
      });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const data = await response.json();
      return data;
    } catch (error) {
      console.error('Supabase fetch error:', error);
      throw error;
    }
  }

  async getListings(options = {}) {
    const { limit = 1000, offset = 0, filters = {} } = options;
    const params = new URLSearchParams();
    params.set('limit', limit);
    params.set('offset', offset);
    
    if (filters.source) params.set('source', filters.source);
    if (filters.transaction) params.set('transaction', filters.transaction);
    if (filters.governorate) params.set('governorate', filters.governorate);
    if (filters.area) params.set('area', filters.area);
    if (filters.price) params.set('price', filters.price);
    
    const url = `${SUPABASE_URL}/rest/v1/market_listings?${params.toString()}`;
    return await this.fetch(url);
  }

  async getListingsCount() {
    const url = `${SUPABASE_URL}/rest/v1/market_listings?select=count&id=gt.0`;
    const data = await this.fetch(url);
    return Array.isArray(data) ? data.length : data.count || 0;
  }

  async getAllListingsPaginated(batchSize = 1000) {
    const all = [];
    let offset = 0;
    let hasMore = true;
    
    while (hasMore) {
      const batch = await this.getListings({ limit: batchSize, offset });
      if (!batch || batch.length === 0) {
        hasMore = false;
      } else {
        all.push(...batch);
        offset += batchSize;
      }
    }
    
    return all;
  }

  async getDevelopments() {
    const url = `${SUPABASE_URL}/rest/v1/market_developments?select=*&orderby=id.desc&limit=500`;
    return await this.fetch(url);
  }

  async getSources() {
    const url = `${SUPABASE_URL}/rest/v1/sources?select=*&orderby=name.asc`;
    return await this.fetch(url);
  }

  async getOpportunities() {
    const url = `${SUPABASE_URL}/rest/v1/opportunities?select=*&orderby=created_at.desc&limit=100`;
    try {
      return await this.fetch(url);
    } catch {
      return [];
    }
  }

  async getClients() {
    const url = `${SUPABASE_URL}/rest/v1/client_requests?select=*&orderby=created_at.desc&limit=100`;
    try {
      return await this.fetch(url);
    } catch {
      return [];
    }
  }

  async getAlerts() {
    const url = `${SUPABASE_URL}/rest/v1/alerts?select=*&orderby=created_at.desc&limit=50`;
    try {
      return await this.fetch(url);
    } catch {
      return [];
    }
  }

  async getOutreachStats() {
    const url = `${SUPABASE_URL}/rest/v1/outreach_stats?select=*&orderby=date.desc&limit=30`;
    try {
      return await this.fetch(url);
    } catch {
      return [];
    }
  }

  // ============================================================================
  // التحليل الذكي
  // ============================================================================

  analyzeListings(listings) {
    const analysis = {
      total: listings.length,
      bySource: {},
      byTransaction: {},
      byGovernorate: {},
      byArea: {},
      priceStats: {
        disclosed: 0,
        undisclosed: 0,
        min: null,
        max: null,
        avg: null,
        median: null,
        prices: [],
      },
      areaStats: {},
      sourceQuality: {},
      timestamp: new Date().toISOString(),
    };

    const prices = [];
    
    for (const listing of listings) {
      // مصدر
      const source = listing.source || 'Unknown';
      analysis.bySource[source] = (analysis.bySource[source] || 0) + 1;
      
      // معاملة
      const tx = listing.transaction || 'Unknown';
      analysis.byTransaction[tx] = (analysis.byTransaction[tx] || 0) + 1;
      
      // محافظة
      const gov = listing.governorate || 'Unknown';
      analysis.byGovernorate[gov] = (analysis.byGovernorate[gov] || 0) + 1;
      
      // منطقة
      const area = listing.area || 'Unknown';
      analysis.byArea[area] = (analysis.byArea[area] || 0) + 1;
      
      // سعر
      if (listing.price && listing.price > 0) {
        const price = Number(listing.price);
        prices.push(price);
        analysis.priceStats.disclosed++;
        if (!analysis.priceStats.min || price < analysis.priceStats.min) {
          analysis.priceStats.min = price;
        }
        if (!analysis.priceStats.max || price > analysis.priceStats.max) {
          analysis.priceStats.max = price;
        }
      } else {
        analysis.priceStats.undisclosed++;
      }
      
      // نوع العقار
      const type = listing.property_type || 'Unknown';
      if (!analysis.areaStats[type]) {
        analysis.areaStats[type] = { count: 0, sources: {}, byGov: {} };
      }
      analysis.areaStats[type].count++;
      analysis.areaStats[type].sources[source] = (analysis.areaStats[type].sources[source] || 0) + 1;
      const gov2 = listing.governorate || 'Unknown';
      analysis.areaStats[type].byGov[gov2] = (analysis.areaStats[type].byGov[gov2] || 0) + 1;
      
      // جودة المصدر
      if (!analysis.sourceQuality[source]) {
        analysis.sourceQuality[source] = {
          total: 0,
          priced: 0,
          withArea: 0,
          withType: 0,
          avgPrice: 0,
        };
      }
      const sq = analysis.sourceQuality[source];
      sq.total++;
      if (listing.price && listing.price > 0) sq.priced++;
      if (listing.area) sq.withArea++;
      if (listing.property_type) sq.withType++;
      if (listing.price && listing.price > 0) {
        sq.avgPrice += Number(listing.price);
      }
    }
    
    // حساب المتوسطات
    for (const source in analysis.sourceQuality) {
      const sq = analysis.sourceQuality[source];
      if (sq.priced > 0) {
        sq.avgPrice = Math.round(sq.avgPrice / sq.priced);
      } else {
        sq.avgPrice = 0;
      }
      sq.pricingRate = Math.round((sq.priced / sq.total) * 100);
      sq.completeness = Math.round(((sq.priced + sq.withArea + sq.withType) / (sq.total * 3)) * 100);
    }
    
    // حساب المتوسط والوسيط للسعر
    if (prices.length > 0) {
      prices.sort((a, b) => a - b);
      const sum = prices.reduce((a, b) => a + b, 0);
      analysis.priceStats.avg = Math.round(sum / prices.length);
      analysis.priceStats.median = prices[Math.floor(prices.length / 2)];
      analysis.priceStats.prices = prices;
    }
    
    return analysis;
  }

  // ============================================================================
  // تقييم الفرص
  // ============================================================================

  calculateOpportunityScore(listing, context = {}) {
    const score = {
      total: 0,
      criteria: {},
      breakdown: [],
    };

    const price = Number(listing.price) || 0;
    const area = Number(listing.space) || 0;
    const hasPrice = price > 0;
    const hasArea = area > 0;
    
    // 1. Presence of price (0-25 points)
    if (hasPrice) {
      score.criteria.pricePresent = 25;
      score.breakdown.push({
        criterion: 'وجود السعر',
        points: 25,
        maxPoints: 25,
        status: 'موجود',
      });
    } else {
      score.criteria.pricePresent = 0;
      score.breakdown.push({
        criterion: 'وجود السعر',
        points: 0,
        maxPoints: 25,
        status: 'غير معلن',
      });
    }

    // 2. Price competitiveness (0-25 points)
    if (hasPrice && context.medianPrice) {
      const ratio = price / context.medianPrice;
      let priceScore;
      if (ratio < 0.7) {
        priceScore = 25;
      } else if (ratio < 0.9) {
        priceScore = 20;
      } else if (ratio < 1.1) {
        priceScore = 15;
      } else if (ratio < 1.3) {
        priceScore = 10;
      } else {
        priceScore = 5;
      }
      score.criteria.priceCompetitiveness = priceScore;
      score.breakdown.push({
        criterion: 'تنافسية السعر',
        points: priceScore,
        maxPoints: 25,
        status: ratio < 1 ? 'أقل من المتوسط' : ratio < 1.2 ? 'متوسط' : 'مرتفع',
        details: `السعر ${ratio.toFixed(2)}× المتوسط`,
      });
    } else {
      score.criteria.priceCompetitiveness = 0;
    }

    // 3. Area information (0-20 points)
    if (hasArea) {
      score.criteria.areaPresent = 15;
      score.breakdown.push({
        criterion: 'وجود المساحة',
        points: 15,
        maxPoints: 20,
        status: 'موجودة',
        details: `${area} م²`,
      });
      
      if (context.avgArea && area > context.avgArea * 1.2) {
        score.criteria.areaValue = 5;
        score.breakdown.push({
          criterion: 'قيمة المساحة',
          points: 5,
          maxPoints: 5,
          status: 'كبيرة',
        });
      } else if (context.avgArea && area < context.avgArea * 0.8) {
        score.criteria.areaValue = 3;
        score.breakdown.push({
          criterion: 'قيمة المساحة',
          points: 3,
          maxPoints: 5,
          status: 'صغيرة',
        });
      } else {
        score.criteria.areaValue = 4;
        score.breakdown.push({
          criterion: 'قيمة المساحة',
          points: 4,
          maxPoints: 5,
          status: 'مناسبة',
        });
      }
    } else {
      score.criteria.areaPresent = 0;
      score.breakdown.push({
        criterion: 'وجود المساحة',
        points: 0,
        maxPoints: 20,
        status: 'غير مذكورة',
      });
    }

    // 4. Source reliability (0-15 points)
    const source = listing.source || 'Unknown';
    const sourceReliability = this.getSourceReliability(source);
    score.criteria.sourceReliability = sourceReliability;
    score.breakdown.push({
      criterion: 'موثوقية المصدر',
      points: sourceReliability,
      maxPoints: 15,
      status: this.getSourceStatusText(source),
    });

    // 5. Transaction type match (0-10 points)
    const tx = listing.transaction || '';
    if (context.preferredTransaction) {
      if (tx.includes(context.preferredTransaction)) {
        score.criteria.transactionMatch = 10;
        score.breakdown.push({
          criterion: 'نوع المعاملة',
          points: 10,
          maxPoints: 10,
          status: 'متطابق',
        });
      } else {
        score.criteria.transactionMatch = 0;
        score.breakdown.push({
          criterion: 'نوع المعاملة',
          points: 0,
          maxPoints: 10,
          status: 'غير متطابق',
          details: tx,
        });
      }
    } else {
      score.criteria.transactionMatch = 5;
      score.breakdown.push({
        criterion: 'نوع المعاملة',
        points: 5,
        maxPoints: 10,
        status: tx || 'غير محدد',
      });
    }

    // 6. Listing freshness (0-5 points)
    const created = new Date(listing.created_at || listing.updated_at || 0);
    const daysOld = (Date.now() - created.getTime()) / (1000 * 60 * 60 * 24);
    let freshnessScore;
    if (daysOld < 1) freshnessScore = 5;
    else if (daysOld < 7) freshnessScore = 4;
    else if (daysOld < 30) freshnessScore = 3;
    else if (daysOld < 90) freshnessScore = 2;
    else freshnessScore = 1;
    
    score.criteria.freshness = freshnessScore;
    score.breakdown.push({
      criterion: 'حديثة',
      points: freshnessScore,
      maxPoints: 5,
      status: `${Math.round(daysOld)} يوم`,
    });

    // حساب المجموع
    score.total = Object.values(score.criteria).reduce((a, b) => a + b, 0);
    
    return score;
  }

  getSourceReliability(source) {
    const reliability = {
      'الفريج': 15,
      'OpenSooq': 12,
      '4Sale': 12,
      'Mourjan': 10,
      'Q8Aqar': 10,
      'Bu3qar': 10,
      'boshamlan': 10,
      'NabdAqar': 10,
      'alhisba': 8,
      'Sakan': 8,
      'Waseet': 7,
      'Aqarat': 7,
      'FindQ8': 6,
      'Yebtah': 6,
      'AlHisba': 8,
      'Boshamlan': 10,
      'officiel': 15,
      'riere': 15,
      'kosmos': 10,
    };
    return reliability[source] || 5;
  }

  getSourceStatusText(source) {
    const reliability = this.getSourceReliability(source);
    if (reliability >= 13) return 'عالي الجودة';
    if (reliability >= 9) return 'جيد';
    if (reliability >= 6) return 'متوسط';
    return 'غير محدد';
  }

  // ============================================================================
  // التوصيات
  // ============================================================================

  generateRecommendations(listings, analysis, context = {}) {
    const recommendations = {
      summary: [],
      topListings: [],
      marketInsights: [],
      alerts: [],
    };

    // 1. أفضل العروض للبيع
    const forSale = listings.filter(l => 
      l.transaction && l.transaction.includes('بيع') && l.transaction.includes('لل')
    );
    const scoredForSale = forSale.map(l => ({
      ...l,
      score: this.calculateOpportunityScore(l, {
        medianPrice: analysis.priceStats.median,
        avgArea: this.getAverageArea(forSale),
        preferredTransaction: 'بيع',
      }).total,
    })).sort((a, b) => b.score - a.score);
    
    recommendations.topListings = scoredForSale.slice(0, 10);
    
    // 2. بالنسبة للإيجار
    const forRent = listings.filter(l => 
      l.transaction && (l.transaction.includes('إيجار') || l.transaction.includes('اجار'))
    );
    const scoredForRent = forRent.map(l => ({
      ...l,
      score: this.calculateOpportunityScore(l, {
        medianPrice: analysis.priceStats.median,
        avgArea: this.getAverageArea(forRent),
        preferredTransaction: 'إيجار',
      }).total,
    })).sort((a, b) => b.score - a.score);
    
    recommendations.rentOpportunities = scoredForRent.slice(0, 10);

    // 3. رؤى السوق
    recommendations.marketInsights = this.generateMarketInsights(analysis, listings);

    // 4. التنبيهات
    recommendations.alerts = this.generateAlerts(analysis, listings);

    return recommendations;
  }

  getAverageArea(listings) {
    const areas = listings
      .filter(l => l.space && Number(l.space) > 0)
      .map(l => Number(l.space));
    if (areas.length === 0) return 0;
    return areas.reduce((a, b) => a + b, 0) / areas.length;
  }

  generateMarketInsights(analysis, listings) {
    const insights = [];
    
    // 인사이트 1: トップソース
    const topSources = Object.entries(analysis.bySource)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);
    insights.push({
      type: 'market_dominance',
      title: 'أقوى مصادر الإعلانات',
      description: `المصدر الأعلى هو "${topSources[0][0]}" بنسبة ${Math.round(topSources[0][1] / analysis.total * 100)}% من الإعلانات`,
      sources: topSources,
    });

    // 인사이트 2: توزيع المعاملات
    const txInsights = Object.entries(analysis.byTransaction)
      .sort((a, b) => b[1] - a[1]);
    insights.push({
      type: 'transaction_split',
      title: 'توزيع أنواع المعاملات',
      description: `المعاملات الرئيسية: ${txInsights.map(t => `${t[0]} (${Math.round(t[1] / analysis.total * 100)}%)`).join(', ')}`,
      data: txInsights,
    });

    // 인사이트 3: أسعار السوق
    if (analysis.priceStats.disclosed > 0) {
      insights.push({
        type: 'price_analysis',
        title: 'واقع أسعار السوق',
        description: `معدل السعر: ${this.formatPrice(analysis.priceStats.avg)} | وسط: ${this.formatPrice(analysis.priceStats.median)} | نطاق: ${this.formatPrice(analysis.priceStats.min)} - ${this.formatPrice(analysis.priceStats.max)}`,
        data: {
          average: analysis.priceStats.avg,
          median: analysis.priceStats.median,
          min: analysis.priceStats.min,
          max: analysis.priceStats.max,
          disclosed: analysis.priceStats.disclosed,
          undisclosed: analysis.priceStats.undisclosed,
          disclosureRate: Math.round((analysis.priceStats.disclosed / analysis.total) * 100),
        },
      });
    }

    // 인사이트 4: المحافظات النشطة
    const topGov = Object.entries(analysis.byGovernorate)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);
    insights.push({
      type: 'active_governorates',
      title: 'أكثر المحافظات نشاطًا',
      description: topGov.map(g => `${g[0]} (${Math.round(g[1] / analysis.total * 100)}%)`).join(', '),
      data: topGov,
    });

    // 인사이트 5: الفجوة في الأسعار
    if (analysis.priceStats.undisclosed > 0) {
      const undisclosedRate = Math.round((analysis.priceStats.undisclosed / analysis.total) * 100);
      insights.push({
        type: 'price_gap',
        title: 'فجوة الأسعار غير المعلنة',
        description: `هناك ${analysis.priceStats.undisclosed} إعلان (${undisclosedRate}%) بدون سعر معلن — يمكن استهدافهم للتواصل`,
        severity: undisclosedRate > 40 ? 'high' : undisclosedRate > 20 ? 'medium' : 'low',
      });
    }

    return insights;
  }

  generateAlerts(analysis, listings) {
    const alerts = [];
    
    // تنبيه 1: زيادة الأسعار
    if (analysis.priceStats.max && analysis.priceStats.max > 500000) {
      alerts.push({
        type: 'high_price',
        severity: 'info',
        title: 'سعر قياسي مرتفع',
        message: `وجدت إعلان بسعر ${this.formatPrice(analysis.priceStats.max)} — ربما فرصة استثمارية أو سعر غير واقعي`,
      });
    }

    // تنبيه 2: Communicating with undisclosed prices
    if (analysis.priceStats.undisclosed > 100) {
      alerts.push({
        type: 'action_item',
        severity: 'action',
        title: 'فرص تواصل',
        message: `${analysis.priceStats.undisclosed} إعلان بدون سعر — مراسلة البائع للحصول على السعر`,
      });
    }

    // تنبيه 3: مصادر قليلة
    const lowSources = Object.entries(analysis.bySource)
      .filter(([_, count]) => count < 5);
    if (lowSources.length > 0) {
      alerts.push({
        type: 'low_coverage',
        severity: 'warning',
        title: 'مصادر قليلة',
        message: `${lowSources.length} مصدر له إعلانات قليلة — قد يحتاج إلى استهداف',
      });
    }

    return alerts;
  }

  formatPrice(price) {
    if (!price || price <= 0) return 'غير معلن';
    if (price >= 1000000) {
      return `${(price / 1000000).toFixed(2)} مليون دينار`;
    }
    if (price >= 1000) {
      return `${(price / 1000).toFixed(1)} ألف دينار`;
    }
    return `${price} دينار`;
  }

  formatNumber(num) {
    if (!num && num !== 0) return 'غير متاح';
    return num.toLocaleString('ar-KW');
  }
}

// Export for use in other modules
window.SupabaseLiveClient = SupabaseLiveClient;
