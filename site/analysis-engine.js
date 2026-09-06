/**
 * analysis-engine.js
 * محرك التحليل والتقييم الذكي — يعمل مع بيانات Supabase الحية
 * يوفر: تحليل السوق، تقييم الفرص، التوصيات الذكية
 */

const AnalysisEngine = {
  /**
   * تحليل شامل للبيانات
   */
  analyze(listings, developments = []) {
    const analysis = {
      metadata: {
        analyzed_at: new Date().toISOString(),
        total_listings: listings.length,
        total_developments: developments.length,
      },
      market_overview: this.marketOverview(listings),
      price_analysis: this.priceAnalysis(listings),
      source_analysis: this.sourceAnalysis(listings),
      geographic_analysis: this.geographicAnalysis(listings),
      opportunity_analysis: this.opportunityAnalysis(listings),
      recommendations: this.generateRecommendations(listings, analysis, developments),
    };
    return analysis;
  },

  marketOverview(listings) {
    const byType = {};
    const byTransaction = {};
    const sources = new Set();
    const governorates = new Set();
    const areas = new Set();
    const priced = 0;
    const withPhone = 0;
    
    for (const listing of listings) {
      // نوع العقار
      const type = listing.property_type || 'غير محدد';
      byType[type] = (byType[type] || 0) + 1;
      
      // نوع المعاملة  
      const tx = listing.transaction || 'غير محدد';
      byTransaction[tx] = (byTransaction[tx] || 0) + 1;
      
      // مصدر
      if (listing.source) sources.add(listing.source);
      
      // محافظة
      if (listing.governorate) governorates.add(listing.governorate);
      
      // منطقة
      if (listing.area) areas.add(listing.area);
      
      // سعر
      if (listing.price && Number(listing.price) > 0) priced++;
    }
    
    return {
      total_listings: listings.length,
      unique_sources: sources.size,
      unique_governorates: governorates.size,
      unique_areas: areas.size,
      priced_listings: priced,
      pricing_rate: listings.length > 0 ? Math.round((priced / listings.length) * 100) : 0,
      by_type: this.sortByCount(byType),
      by_transaction: this.sortByCount(byTransaction),
      top_sources: this.getTopSources(listings, 10),
    };
  },

  priceAnalysis(listings) {
    const prices = listings
      .filter(l => l.price && Number(l.price) > 0)
      .map(l => Number(l.price))
      .sort((a, b) => a - b);
    
    if (prices.length === 0) {
      return {
        has_data: false,
        count: 0,
      };
    }
    
    const sum = prices.reduce((a, b) => a + b, 0);
    const avg = Math.round(sum / prices.length);
    const median = prices[Math.floor(prices.length / 2)];
    const min = prices[0];
    const max = prices[prices.length - 1];
    
    // فئات الأسعار
    const priceRanges = {
      under_50k: prices.filter(p => p < 50000).length,
      p50k_to_100k: prices.filter(p => p >= 50000 && p < 100000).length,
      p100k_to_500k: prices.filter(p => p >= 100000 && p < 500000).length,
      p500k_to_1m: prices.filter(p => p >= 500000 && p < 1000000).length,
      over_1m: prices.filter(p => p >= 1000000).length,
    };
    
    // حساب سعر المتر (إذا كانت المساحات متاحة)
    const pricePerM2 = [];
    for (const listing of listings) {
      const price = Number(listing.price);
      const area = Number(listing.space);
      if (price > 0 && area > 0) {
        pricePerM2.push({ price, area, perM2: price / area });
      }
    }
    
    const avgPerM2 = pricePerM2.length > 0
      ? Math.round(pricePerM2.reduce((a, b) => a + b.perM2, 0) / pricePerM2.length)
      : null;
    
    return {
      has_data: true,
      count: prices.length,
      average: avg,
      median: median,
      min: min,
      max: max,
      price_ranges: priceRanges,
      average_price_per_m2: avgPerM2,
      price_per_m2_samples: pricePerM2.slice(0, 10),
    };
  },

  sourceAnalysis(listings) {
    const sourceStats = {};
    
    for (const listing of listings) {
      const source = listing.source || 'غير معرف';
      if (!sourceStats[source]) {
        sourceStats[source] = {
          total: 0,
          priced: 0,
          with_area: 0,
          with_location: 0,
          total_price: 0,
        };
      }
      const stats = sourceStats[source];
      stats.total++;
      if (listing.price && Number(listing.price) > 0) {
        stats.priced++;
        stats.total_price += Number(listing.price);
      }
      if (listing.space && Number(listing.space) > 0) stats.with_area++;
      if (listing.governorate) stats.with_location++;
    }
    
    // حساب المؤشرات لكل مصدر
    const sources = Object.entries(sourceStats).map(([name, stats]) => ({
      name,
      total: stats.total,
      priced: stats.priced,
      with_area: stats.with_area,
      with_location: stats.with_location,
      pricing_rate: stats.total > 0 ? Math.round((stats.priced / stats.total) * 100) : 0,
      completeness_rate: stats.total > 0 ? Math.round(((stats.priced + stats.with_area + stats.with_location) / (stats.total * 3)) * 100) : 0,
      avg_price: stats.priced > 0 ? Math.round(stats.total_price / stats.priced) : null,
      reliability_score: this.calculateSourceReliability(name, stats),
    })).sort((a, b) => b.total - a.total);
    
    return {
      total_sources: sources.length,
      sources: sources,
      top_by_volume: sources.slice(0, 10),
      most_comprehensive: sources.filter(s => s.completeness_rate > 70).slice(0, 5),
    };
  },

  calculateSourceReliability(name, stats) {
    const baseScore = 50;
    const volumeBonus = Math.min(30, (stats.total / 100) * 10);
    const pricingBonus = (stats.pricing_rate / 100) * 10;
    const completenessBonus = (stats.completeness_rate / 100) * 10;
    return Math.min(100, Math.round(baseScore + volumeBonus + pricingBonus + completenessBonus));
  },

  geographicAnalysis(listings) {
    const byGovernorate = {};
    const byArea = {};
    
    for (const listing of listings) {
      const gov = listing.governorate || 'غير محدد';
      byGovernorate[gov] = (byGovernorate[gov] || 0) + 1;
      
      const area = listing.area || 'غير محدد';
      byArea[area] = (byArea[area] || 0) + 1;
    }
    
    const govList = Object.entries(byGovernorate)
      .sort((a, b) => b[1] - a[1]);
    
    const areaList = Object.entries(byArea)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 20);
    
    return {
      total_governorates: govList.length,
      total_areas: byArea.length,
      by_governorate: govList,
      top_areas: areaList,
      most_active_governorate: govList[0]?.[0] || 'غير محدد',
      most_active_governorate_count: govList[0]?.[1] || 0,
    };
  },

  opportunityAnalysis(listings) {
    // تحديد أفضل الفرص للشراء
    const buyOpportunities = listings.filter(l => {
      const tx = l.transaction || '';
      return tx.includes('بيع') || tx.includes('لل') || tx.includes('شراء');
    });
    
    // تحديد أفضل الفرص للإيجار
    const rentOpportunities = listings.filter(l => {
      const tx = l.transaction || '';
      return tx.includes('إيجار') || tx.includes('اجار') || tx.includes('إستهلاك');
    });
    
    // Calculate opportunity scores
    const scoredBuy = this.scoreOpportunities(buyOpportunities, 'بيع');
    const scoredRent = this.scoreOpportunities(rentOpportunities, 'إيجار');
    
    return {
      buy_opportunities: {
        total: buyOpportunities.length,
        scored: scoredBuy.slice(0, 20),
        top_10: scoredBuy.slice(0, 10),
      },
      rent_opportunities: {
        total: rentOpportunities.length,
        scored: scoredRent.slice(0, 20),
        top_10: scoredRent.slice(0, 10),
      },
      total_opportunities: buyOpportunities.length + rentOpportunities.length,
    };
  },

  scoreOpportunities(listings, type) {
    return listings.map(listing => {
      const score = {
        listing: listing,
        total: 0,
        criteria: {},
        breakdown: [],
      };
      
      // معايير التقييم
      const criteria = {
        price_present: this.criteriaPricePresent(listing),
        price_competitiveness: this.criteriaPriceCompetitiveness(listing, type),
        area_present: this.criteriaAreaPresent(listing),
        source_reliability: this.criteriaSourceReliability(listing),
        listing_freshness: this.criteriaFreshness(listing),
        transaction_match: this.criteriaTransactionMatch(listing, type),
      };
      
      score.criteria = criteria;
      score.total = Object.values(criteria).reduce((a, b) => a + b, 0);
      score.breakdown = Object.entries(criteria).map(([key, value]) => ({
        criterion: key.replace(/_/g, ' '),
        points: value,
        max_points: 25,
        percentage: Math.round((value / 25) * 100),
      }));
      
      return score;
    }).sort((a, b) => b.total - a.total);
  },

  criteriaPricePresent(listing) {
    const price = Number(listing.price);
    if (price > 0) return 25;
    if (listing.price_text) return 15;
    return 0;
  },

  criteriaPriceCompetitiveness(listing, type) {
    const price = Number(listing.price);
    if (price <= 0) return 0;
    
    // معيار نسبي - يمكن أن يصبح أكثر ذكاءً مع المزيد من البيانات
    if (type === 'بيع') {
      if (price < 50000) return 25;
      if (price < 100000) return 22;
      if (price < 200000) return 18;
      if (price < 500000) return 15;
      return 10;
    } else {
      if (price < 500) return 25;
      if (price < 1000) return 22;
      if (price < 2000) return 18;
      if (price < 5000) return 15;
      return 10;
    }
  },

  criteriaAreaPresent(listing) {
    const area = Number(listing.space);
    if (area > 0) {
      if (area >= 100) return 20;
      if (area >= 50) return 18;
      if (area >= 20) return 15;
      return 10;
    }
    return 0;
  },

  criteriaSourceReliability(listing) {
    const source = listing.source || '';
    const reliableSources = ['الفريج', 'OpenSooq', '4Sale', 'Mourjan', 'Q8Aqar', 'Bu3qar', 'boshamlan'];
    if (reliableSources.some(s => source.includes(s))) return 20;
    return 10;
  },

  criteriaFreshness(listing) {
    const date = new Date(listing.created_at || listing.updated_at || 0);
    const daysOld = (Date.now() - date.getTime()) / (1000 * 60 * 60 * 24);
    if (daysOld < 1) return 10;
    if (daysOld < 7) return 8;
    if (daysOld < 30) return 5;
    if (daysOld < 90) return 3;
    return 1;
  },

  criteriaTransactionMatch(listing, type) {
    const tx = (listing.transaction || '').toLowerCase();
    const typeLower = type.toLowerCase();
    if (tx.includes(typeLower) || tx.includes(typeLower.replace('ة', ''))) return 15;
    return 5;
  },

  generateRecommendations(listings, analysis, developments) {
    const recommendations = {
      top_opportunities: [],
      market_trends: [],
      action_items: [],
      insights: [],
    };

    // أفضل 10 فرص للشراء
    const buyScored = this.scoreOpportunities(
      listings.filter(l => (l.transaction || '').toLowerCase().includes('بيع') || (l.transaction || '').toLowerCase().includes('لل')),
      'بيع'
    );
    recommendations.top_opportunities = buyScored.slice(0, 10).map(s => ({
      ...s.listing,
      score: s.total,
      price: s.listing.price,
      area: s.listing.space,
      source: s.listing.source,
    }));

    // اتجاهات السوق
    recommendations.market_trends = [
      {
        title: 'تركيز المصادر',
        description: `أعلى مصدر 비스وع: ${analysis.source_analysis.top_by_volume[0]?.name || 'غير محدد'} (${analysis.source_analysis.top_by_volume[0]?.total || 0} إعلان)`,
        type: 'source_concentration',
      },
      {
        title: 'نشر المعاملات',
        description: Object.entries(analysis.market_overview.by_transaction)
          .sort((a, b) => b[1] - a[1])
          .map(([tx, count]) => `${tx}: ${count}`)
          .join(', '),
        type: 'transaction_distribution',
      },
    ];

    // عناصر العمل
    if (analysis.price_analysis.has_data) {
      recommendations.action_items.push({
        type: 'price_strategy',
        title: 'مراجعة استراتيجية الأسعار',
        description: `متوسط السعر: ${this.formatPrice(analysis.price_analysis.average)} | وسط: ${this.formatPrice(analysis.price_analysis.median)}`,
      });
    }
    
    if (analysis.market_overview.pricing_rate < 50) {
      recommendations.action_items.push({
        type: 'data_quality',
        title: 'تحسين جودة البيانات',
        description: `فقط ${analysis.market_overview.pricing_rate}% من الإعلانات تحتوي على أسعار — ضروري لتحسين التحليل`,
      });
    }

    // رؤى أذكى
    recommendations.insights = this.generateAdvancedInsights(listings, analysis);

    return recommendations;
  },

  generateAdvancedInsights(listings, analysis) {
    const insights = [];
    
    // 1. تحديد الأسواق الناشئة
    const govActivity = analysis.geographic_analysis.by_governorate.slice(0, 5);
    if (govActivity.length > 0) {
      insights.push({
        title: 'أكثر المناطق نشاطًا',
        description: govActivity.map(g => `${g[0]}: ${g[1]} إعلان (${Math.round(g[1] / analysis.market_overview.total_listings * 100)}%)`).join(', '),
        type: 'hot_regions',
      });
    }

    // 2. فجوة الأسعار
    if (analysis.price_analysis.has_data) {
      const undisclosed = analysis.market_overview.total_listings - analysis.price_analysis.count;
      if (undisclosed > 100) {
        insights.push({
          title: 'فرص التواصل المباشر',
          description: `${undisclosed} إعلان بدون سعر معلن — مراسلة البائعين للحصول على التسعير`,
          type: 'contact_opportunity',
          priority: 'high',
        });
      }
    }

    // 3. تحليل المصدر الموثوق
    const reliableSources = analysis.source_analysis.sources.filter(s => s.reliability_score > 70);
    if (reliableSources.length > 0) {
      insights.push({
        title: 'أفضل المصادر الموثوقة',
        description: reliableSources.slice(0, 3).map(s => `${s.name} (جودة: ${s.reliability_score}%)`).join(', '),
        type: 'trusted_sources',
      });
    }

    // 4. تنوع أنواع العقارات
    const types = Object.keys(analysis.market_overview.by_type);
    if (types.length > 5) {
      insights.push({
        title: 'تنوع أنواع العقارات',
        description: `${types.length} نوع عقار مختلف في السوق`,
        type: 'property_diversity',
      });
    }

    return insights;
  },

  sortByCount(obj) {
    return Object.entries(obj)
      .sort((a, b) => b[1] - a[1])
      .map(([key, value]) => ({ name: key, count: value }));
  },

  getTopSources(listings, limit) {
    const sourceCounts = {};
    for (const listing of listings) {
      const source = listing.source || 'غير معرف';
      sourceCounts[source] = (sourceCounts[source] || 0) + 1;
    }
    return Object.entries(sourceCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, limit)
      .map(([name, count]) => ({ name, count }));
  },

  formatPrice(price) {
    if (!price || price <= 0) return 'غير معلن';
    if (price >= 1000000) {
      return `${(price / 1000000).toFixed(2)} مليون دينار`;
    }
    if (price >= 1000) {
      return `${(price / 1000).toFixed(1)} ألف دينار`;
    }
    return `${price} دينار`;
  },

  formatNumber(num) {
    if (!num && num !== 0) return 'غير متاح';
    return num.toLocaleString('ar-KW');
  },
};

window.AnalysisEngine = AnalysisEngine;
