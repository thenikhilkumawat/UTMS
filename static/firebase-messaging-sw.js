/* static/firebase-messaging-sw.js
   Firebase Cloud Messaging Service Worker for Uttam Tailors
   This file must live at the root of the site (/firebase-messaging-sw.js)
   — it is served via a Flask route that reads from /static/. */

importScripts('https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.12.0/firebase-messaging-compat.js');

// Firebase config is injected by the page via postMessage after SW installs,
// or we read it from the URL query param passed during registration.
// Fallback: hard-coded after admin sets it up.
let _firebaseConfig = null;

self.addEventListener('message', function(event) {
  if (event.data && event.data.type === 'FIREBASE_CONFIG') {
    _firebaseConfig = event.data.config;
    _initFirebase();
  }
});

function _initFirebase() {
  if (!_firebaseConfig) return;
  try {
    if (!firebase.apps.length) {
      firebase.initializeApp(_firebaseConfig);
    }
    const messaging = firebase.messaging();

    messaging.onBackgroundMessage(function(payload) {
      const n = payload.notification || {};
      const d = payload.data || {};
      const title = n.title || 'Uttam Tailors';
      const body  = n.body  || 'You have a new notification';
      const icon  = n.icon  || '/static/img/logo.png';
      const url   = d.url   || 'https://uttamtailors.in/track-order';

      self.registration.showNotification(title, {
        body:    body,
        icon:    icon,
        badge:   '/static/img/badge.png',
        vibrate: [200, 100, 200],
        data:    { url: url },
        actions: [{ action: 'track', title: 'Track Order' }],
      });
    });
  } catch(e) {
    console.warn('[SW] Firebase init error:', e);
  }
}

self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url)
    ? event.notification.data.url
    : 'https://uttamtailors.in/track-order';
  event.waitUntil(clients.openWindow(url));
});
