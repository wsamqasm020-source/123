/**
 * Service Worker - نظام تسجيل الحضور
 * يدعم العمل الكامل بدون إنترنت
 */

const CACHE_NAME = 'attendance-v5';

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

// ===== INSTALL =====
self.addEventListener('install', (event) => {
  console.log('[SW] Installing v4...');
  self.skipWaiting();

  event.waitUntil(
    caches.open(CACHE_NAME).then(async (cache) => {
      // ✅ فقط الملفات الثابتة - لا نخزن صفحات HTML هنا لأن Flask يعمل redirects
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

  // ===== لا تتدخل في تسجيل الدخول =====
  if (url.pathname === '/login') return;

  // ===== API: لا تتدخل - اتركها تروح للسيرفر مباشرة =====
  if (url.pathname.startsWith('/api/')) {
    return; // ✅ الـ SW ما يتدخل بأي طلب API
  }

  // ===== صفحات HTML: شبكة أولاً، كاش ثانياً =====
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request, { redirect: 'follow' })
        .then(response => {
          // ✅ فقط خزّن GET requests - POST ممنوع بالكاش
          if (response.ok && event.request.method === 'GET') {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
          }
          return response;
        })
        .catch(async () => {
          console.log('[SW] Offline - serving from cache:', url.pathname);
          const cached = await caches.match(event.request);
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
  // ✅ فقط GET requests
  if (event.request.method !== 'GET') return;

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