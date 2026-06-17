// Uttam UTMS — Service Worker
// During active development: NO caching of CSS/JS — always fetch fresh from network.
// This prevents stale styles from showing in the installed PWA app.
const CACHE = 'utms-v2-nocache';

self.addEventListener('install', e => {
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  // Clear ALL old caches from previous service worker versions
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// No fetch handler — let the browser handle all requests normally (always network).
// This ensures CSS/JS changes show up immediately without needing to clear cache.
