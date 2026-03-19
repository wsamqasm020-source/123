/**
 * Service Worker - نظام تسجيل الحضور
 * يدعم العمل الكامل بدون إنترنت
 */

const CACHE_NAME = 'attendance-v10';

// كل الملفات اللي تحتاجها الصفحات للعمل offline
const STATIC_ASSETS = [
  '/',
  '/login',
  '/scanner',
  '/attendance',
  '/students',
  '/subjects',
  '/generate',
  '/settings',
  '/offline.html',
  '/static/css/style.css',
  '/static/css/bootstrap.min.css',
  '/static/js/app.js',
  '/static/js/bootstrap.bundle.min.js',
  '/static/js/html5-qrcode.min.js'
];

// ===== INSTALL =====
self.addEventListener('install', (event) => {
  console.log('[SW] Installing...');
  self.skipWaiting();

  event.waitUntil(
    caches.open(CACHE_NAME).then(async (cache) => {
      for (const url of STATIC_ASSETS) {
        try {
          const response = await fetch(url, { cache: 'no-cache' });
          if (response.ok) {
            await cache.put(url, response);
            console.log('[SW] ✅ Cached:', url);
          } else {
            console.warn('[SW] ⚠️ Failed to cache:', url, 'Status:', response.status);
          }
        } catch (e) {
          console.warn('[SW] ⚠️ Could not fetch:', url, '-', e.message);
        }
      }
      console.log('[SW] Pre-caching completed');
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

  // ===== لا تتدخل في صفحات حساسة (POST requests) =====
  if (url.pathname === '/login' || url.pathname === '/logout' || 
      url.pathname === '/update-settings' || url.pathname === '/settings') return;

  // ===== API: لا تتدخل - اتركها تروح للسيرفر مباشرة =====
  if (url.pathname.startsWith('/api/')) {
    return; // ✅ الـ SW ما يتدخل بأي طلب API
  }

  // ===== صفحات HTML: شبكة أولاً، كاش ثانياً =====
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request, { redirect: 'follow' })
        .then(response => {
          if (response.ok && event.request.method === 'GET') {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(cache => {
              cache.put(event.request, clone).catch(e => console.warn('[SW] Cache error:', e.message));
            });
          }
          return response;
        })
        .catch(async () => {
          console.log('[SW] Offline - trying cache for:', event.request.url);
          const cached = await caches.match(event.request);
          if (cached) {
            console.log('[SW] Serving from cache:', event.request.url);
            return cached;
          }
          
          // جرب الصفحة الرئيسية
          const root = await caches.match('/');
          if (root) return root;

          // صفحة offline كملاذ أخير
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

  // تجاهل الملفات الديناميكية والـ uploads
  if (url.pathname.startsWith('/static/uploads/')) {
    return;
  }

  event.respondWith(
    caches.match(event.request).then(cached => {
      if (cached) return cached;

      return fetch(event.request)
        .then(response => {
          // فقط احفظ الملفات الثابتة الصغيرة (CSS, JS)
          if (response && response.ok && (url.pathname.endsWith('.css') || url.pathname.endsWith('.js'))) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(cache => {
              cache.put(event.request, clone).catch(e => console.warn('[SW] Could not cache:', url.pathname, e.message));
            });
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