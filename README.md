# نظام تسجيل الحضور بالـ QR

نظام إدارة الحضور والغياب باستخدام رموز QR للطلاب - يعمل بدون إنترنت!

## المميزات

- ✅ تسجيل الحضور بمسح QR code
- ✅ توليد QR codes للطلاب
- ✅ إدارة المواد والطلاب
- ✅ سجل الحضور الكامل
- ✅ **يعمل بدون إنترنت (PWA)**
- ✅ تصميم متجاوب مع جميع الأجهزة

## متطلبات النشر على Railway

### الخطوة 1: إنشاء مشروع على Railway

1. سجل دخولك على [Railway](https://railway.app)
2. أنشئ مشروع جديد (New Project)
3. اختر "Deploy from GitHub repo" أو "Empty Project"

### الخطوة 2: رفع الملفات

#### الطريقة الأولى: GitHub (موصى بها)

1. أنشئ repository جديد على GitHub
2. ارفع جميع الملفات الموجودة في هذا المجلد
3. في Railway، اربط المشروع بـ GitHub repo

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

#### الطريقة الثانية: Railway CLI

```bash
# تثبيت Railway CLI
npm install -g @railway/cli

# تسجيل الدخول
railway login

# ربط المشروع
railway link

# النشر
railway up
```

### الخطوة 3: إضافة Domain (اختياري)

1. في لوحة التحكم Railway، اذهب إلى Settings
2. اضغط على "Generate Domain" أو "Custom Domain"
3. ستحصل على رابط مثل: `https://your-app.up.railway.app`

### الخطوة 4: التحقق من PWA

1. افتح الموقع في Chrome
2. افتح DevTools (F12)
3. اذهب إلى Application > Service Workers
4. تأكد أن Service Worker مسجل ومفعل
5. اذهب إلى Application > Manifest
6. تأكد من ظهور جميع البيانات بشكل صحيح

## هيكل المشروع

```
.
├── app.py                 # التطبيق الرئيسي (Flask)
├── database.py            # قاعدة البيانات
├── requirements.txt       # متطلبات Python
├── Procfile              # إعدادات Railway
├── runtime.txt           # إصدار Python
├── nixpacks.toml         # إعدادات البناء
├── static/               # الملفات الثابتة
│   ├── css/
│   │   ├── bootstrap.min.css
│   │   └── style.css
│   ├── js/
│   │   ├── bootstrap.bundle.min.js
│   │   ├── html5-qrcode.min.js
│   │   └── app.js
│   ├── icons/            # أيقونات PWA
│   │   ├── icon-72x72.png
│   │   ├── icon-96x96.png
│   │   ├── icon-128x128.png
│   │   ├── icon-144x144.png
│   │   ├── icon-152x152.png
│   │   ├── icon-192x192.png
│   │   ├── icon-384x384.png
│   │   └── icon-512x512.png
│   ├── sw.js             # Service Worker
│   ├── manifest.json     # PWA Manifest
│   └── offline.html      # صفحة عدم الاتصال
└── templates/            # قوالب HTML
    ├── base.html
    ├── login.html
    ├── index.html
    ├── generate.html
    ├── scanner.html
    ├── students.html
    ├── student_detail.html
    ├── subjects.html
    ├── attendance.html
    └── settings.html
```

## إعدادات PWA

### Service Worker (sw.js)

- يخزن الملفات الأساسية مسبقاً
- يتعامل مع طلبات الشبكة بذكاء
- يوفر صفحة offline عند فقدان الاتصال

### Manifest (manifest.json)

- يحدد إعدادات التطبيق
- يحتوي على الأيقونات بجميع الأحجام
- يدعم اللغة العربية والاتجاه من اليمين لليسار

## استكشاف الأخطاء

### المشكلة: Service Worker لا يعمل

**الحل:**
1. تأكد أن الموقع يستخدم HTTPS (Railway يوفره تلقائياً)
2. افتح Console في DevTools وابحث عن رسائل خطأ
3. تأكد من أن مسار sw.js صحيح (`/static/sw.js`)

### المشكلة: الأيقونات لا تظهر

**الحل:**
1. تأكد من وجود جميع ملفات الأيقونات في `static/icons/`
2. تحقق من مسارات الأيقونات في `manifest.json`
3. تأكد من أن الأيقونات بصيغة PNG

### المشكلة: التطبيق لا يعمل offline

**الحل:**
1. تأكد من تسجيل Service Worker بنجاح
2. افتح Application > Cache Storage وتحقق من وجود الكاش
3. جرب فتح الموقع بدون إنترنت بعد أول زيارة

## تسجيل الدخول الافتراضي

- **اسم المستخدم:** `admin`
- **كلمة المرور:** `admin`

> ⚠️ **تنبيه:** قم بتغيير كلمة المرور الافتراضية فوراً!

## الدعم

إذا واجهت أي مشاكل، تأكد من:
1. أن جميع الملفات مرفوعة بشكل صحيح
2. أن إعدادات Railway صحيحة
3. أن الموقع يستخدم HTTPS

---

تم التطوير بواسطة **قاسم وسام** 🚀
