/**
 * Service Worker - نظام تسجيل الحضور
 * يدعم العمل الكامل بدون إنترنت
 */

const CACHE_NAME = 'attendance-v9';

// كل الملفات اللي تحتاجها الصفحات للعمل offline
const STATIC_ASSETS = [
  '/offline.html',
  '/static/css/style.css',
  '/static/css/bootstrap.min.css',
  '/static/js/app.js',
  '/static/js/bootstrap.bundle.min.js',
  '/static/js/html5-qrcode.min.js',
  '/static/icons/icon-192x192.png',
  '/static/icons/icon-512x512.png'
];

// صفحات HTML اللي نخزنها للـ offline
const HTML_PAGES = [
  '/login',
  '/scanner',
  '/generate',
  '/students',
  '/subjects',
  '/attendance',
  '/settings'
];

// ===== INSTALL =====
self.addEventListener('install', (event) => {
  console.log('[SW] Installing v2...');
  self.skipWaiting();

  event.waitUntil(
    caches.open(CACHE_NAME).then(async (cache) => {
      // خزّن الملفات الثابتة
      for (const url of STATIC_ASSETS) {
        try {
          const response = await fetch(url, { cache: 'no-cache' });
          if (response.ok) {
            await cache.put(url, response);
            console.log('[SW] Cached:', url);
          }
        } catch (e) {
          console.warn('[SW] Could not cache:', url);
        }
      }

      // خزّن صفحات HTML - نتجاهل أي redirect
      for (const url of HTML_PAGES) {
        try {
          const response = await fetch(url, { cache: 'no-cache' });
          if (response.ok && response.type === 'basic') {
            await cache.put(url, response);
            console.log('[SW] Cached page:', url);
          }
        } catch (e) {
          console.warn('[SW] Could not cache page:', url);
        }
      }

      console.log('[SW] Pre-caching done');
    })
  );
});

// ===== ACTIVATE =====
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating v2...');
  event.waitUntil(
    Promise.all([
      self.clients.claim(),
      caches.keys().then((keys) =>
        Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => {
          console.log('[SW] Deleting old cache:', k);
          return caches.delete(k);
        }))
      )
    ])
  );
});

// ===== FETCH =====
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // تجاهل chrome-extension وغيرها
  if (url.protocol !== 'http:' && url.protocol !== 'https:') return;
  if (url.origin !== location.origin) return;

  // ===== API: لا تتدخل - اتركها تروح للسيرفر مباشرة =====
  if (url.pathname.startsWith('/api/')) {
    return; // ✅ الـ SW ما يتدخل بأي طلب API
  }

  // ===== صفحات HTML: شبكة أولاً، كاش ثانياً =====
  if (event.request.mode === 'navigate') {
    // ✅ تجاهل logout و login - Flask يعمل redirect فيها
    if (url.pathname === '/logout' || url.pathname === '/login' || url.pathname === '/') {
      return;
    }

    event.respondWith(
      fetch(event.request)
        .then(response => {
          // ✅ فقط خزّن الردود الناجحة وليست redirects
          if (response.ok && response.status === 200 && response.type === 'basic') {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(cache => {
              try { cache.put(event.request, clone); } catch(e) {}
            });
          }
          return response;
        })
        .catch(async () => {
          console.log('[SW] Offline - serving from cache:', url.pathname);
          const cached = await caches.match(url.pathname);
          if (cached) return cached;

          // جرب الصفحة الرئيسية
          const root = await caches.match('/');
          if (root) return root;

          // صفحة offline
          const offline = await caches.match('/offline.html');
          if (offline) return offline;

          return new Response('<h1 style="font-family:Arial;text-align:center;margin-top:100px;direction:rtl">غير متصل بالإنترنت</h1>',
            { headers: { 'Content-Type': 'text/html; charset=utf-8' } }
          );
        })
    );
    return;
  }

  // ===== ملفات ثابتة: كاش أولاً، شبكة ثانياً =====
  event.respondWith(
    caches.match(event.request).then(cached => {
      if (cached) return cached;

      return fetch(event.request)
        .then(response => {
          if (response && response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
          }
          return response;
        })
        .catch(() => {
          // إذا صورة، ارجع صورة placeholder
          if (event.request.destination === 'image') {
            return new Response('', { status: 404 });
          }
          return new Response('', { status: 503 });
        });
    })
  );
});

// ===== Background Sync =====
self.addEventListener('sync', (event) => {
  if (event.tag === 'sync-attendance') {
    event.waitUntil(syncPendingAttendance());
  }
});

async function syncPendingAttendance() {
  console.log('[SW] Background sync triggered');
  // المزامنة تتم من app.js
}

self.addEventListener('message', (event) => {
  if (event.data === 'skipWaiting') {
    self.skipWaiting();
  }
});

console.log('[SW] Service Worker v2 loaded');