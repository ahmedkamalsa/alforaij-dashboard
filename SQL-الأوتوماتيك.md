# SQL-الأوتوماتيك.md

## جداول Supabase الآلية للمشروع alforaijboard

### نظرة عامة

هذا الملف يشرح الخطوات اللازمة لتشغيل الجداول الآلية في Supabase يدويًا (بسبب الحاجة إلى صلاحيات مباشرة في قاعدة البيانات).

### الجداول المطلوبة

#### ١. جدول `sources` — مصادر الإعلانات المركزية

**الغرض:** تتبع مصادر الإعلانات (OpenSooq, 4Sale, Mourjan, إلخ).

**الملف:** `sql/alforaijboard-full-schema.sql` (الأسطر 25-56)

**الحقول:**
- id, name, url, type, transaction_types, reliability, last_checked, notes, created_at

**السياسات (RLS):**
- anon: SELECT فقط
- service_role: SELECT, INSERT, UPDATE

---

#### ٢. جدول `governorates` — المحافظات

**الغرض:** حفظ المحافظات الكويتية (العاصمة, الأحمدي, الجهراء, مبارك الكبير).

**الملف:** `sql/alforaijboard-full-schema.sql` (الأسطر 62-80)

**الحقول:**
- id, name_ar, name_en, region, created_at

**RLS:** SELECT للجميع (anon + service)

---

#### ٣. جدول `areas` — المناطق داخل كل محافظة

**الغرض:** ربط المناطق (السالمية, الرياض, الشويخ, إلخ) بمحافظتها.

**الملف:** `sql/geographic-update.sql` (الأسطر 12-27)

**RLS:** SELECT للجميع

---

#### ٤. جدول `cron_results` — سجل نتائج الكرون

**الغرض:** حفظ نتائج تشغيل الكرون اليومي (تحليل السوق, تحديث قاعدة البيانات).

**الملف:** `sql/alforaijboard-full-schema.sql` (جزء من الجداول "المعلّقة")

**الحقول المقترحة:**
- id, job_name, started_at, completed_at, status, duration_seconds, data_summary, error_message

**RLS:**
- anon: SELECT فقط
- service_role: SELECT, INSERT

---

#### ٥. جدول `projects_log` — سجل مشروع الأتمتة

**الغرض:** سجل الأحداث العامة للمشروع (تحديثات, فشل, نجاح).

**الملف:** `sql/alforaijboard-full-schema.sql`

**RLS:** service_role فقط (أو anon SELECT محدود)

---

#### ٦. جدول `memories` — الذاكرة طويلة المدى

**الغرض:** تخزين حقائق مكتسبة عبر الزمن عن السوق العقاري.

**الملف:** `sql/alforaijboard-full-schema.sql`

**RLS:** service_roleoggle

---

### طريقة التنفيذ اليدوية

#### خطوة ١: فتح Supabase SQL Editor

1. روح على `https://supabase.com/dashboard/project/bwspcsiazbwrrxpgoldx/sql`
2. افتح SQL Editor

#### خطوة ٢: تنفيذ ملف `alforaijboard-full-schema.sql`

انسخ **كامل المحتوى** من `sql/alforaijboard-full-schema.sql` والصقه في SQL Editor，然后 تشغيل.

```
▶ Run (Ctrl+Enter)
```

#### خطوة ٣: تنفيذ ملف `geographic-update.sql`

انسخ محتوى `sql/geographic-update.sql` وتشغيل.

هذا الملف:
- ينشئ `governorates` و `areas` (لو ما كانوا موجودين)
- يملأ محافظات كويت (٦ محافظات رئيسية)
- يربط المناطق بـ market_listings

---

### ملاحظات هامة

1. **الترتيب مهم:** `full-schema.sql` أولاً → `geographic-update.sql` بعدين
2. **إذا هناك تعارض:** DELETE أو TRUNCATE الجداول قبل إعادة التشغيل
3. **RLS:** كل الجداول بيكون فيها RLS مفعل — لو حابة ترفع صلاحيات أكثر，روح على Supabase Dashboard

---

### استعلامات مفيدة للتحقق

بعد التنفيذ，جرب:

```sql
--التحقق: عدد الجداول 创建ت
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';

--التحقق: عدد المصادر
SELECT COUNT(*) FROM public.sources;

--التحقق: عدد المحافظات
SELECT COUNT(*) FROM public.governorates;

--التحقق: عدد المناطق
SELECT COUNT(*) FROM public.areas;

--التحقق: market_listings لها governorate و area
SELECT COUNT(*) FROM public.market_listings WHERE governorate IS NOT NULL;
SELECT COUNT(*) FROM public.market_listings WHERE area IS NOT NULL;
```

---

### ماكل الجداول "المعلّقة" ( 미사용약정 )

ذكر في السياق أن الجداول التالية "should create" لكن لم تنفذ بعد:

- `cron_results`
- `projects_log`
- `memories`

لمفي Reasons:
1. ملف `alforaijboard-full-schema.sql` يكون فيه CREATE TABLE IF NOT EXISTS لهذه الجداول
2. لكنه لم ينفذ لأنه يحتاج يدويًا (كمان ذكر في الذاكرة)
3. لو حابة تنفذهم، روح على Supabase SQL Editor وانسخ الكود

---

### Resources إضافية

- Supabase SQL Editor: `https://supabase.com/dashboard/project/bwspcsiazbwrrxpgoldx/sql`
- الوثائق: `https://supabase.com/docs/guides/database`
- RLS: `https://supabase.com/docs/guides/database/postgres/principles/rbac`
