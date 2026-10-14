/* Reptile Manager service worker — app-shell caching, never caches API data. */
const VERSION = 'rm-v1.4.0'
const SHELL = ['./', './index.html', './manifest.json', './icons/icon-192.png', './icons/icon-512.png']

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting()))
})

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  )
})

self.addEventListener('fetch', (e) => {
  const req = e.request
  if (req.method !== 'GET') return
  const url = new URL(req.url)
  if (url.origin !== self.location.origin) return
  // Live data and runtime config always come from the network
  if (url.pathname.includes('/api/') || url.pathname.endsWith('/api-config.js')) return

  // Page navigations: network first, fall back to cached shell (offline start)
  if (req.mode === 'navigate') {
    e.respondWith(
      fetch(req)
        .then((res) => { const copy = res.clone(); caches.open(VERSION).then((c) => c.put('./index.html', copy)); return res })
        .catch(() => caches.match('./index.html'))
    )
    return
  }

  // Hashed build assets, fonts, icons, photos: cache first
  if (url.pathname.includes('/assets/') || url.pathname.includes('/icons/') || url.pathname.includes('/uploads/')) {
    e.respondWith(
      caches.match(req).then((hit) => hit || fetch(req).then((res) => {
        if (res.ok) { const copy = res.clone(); caches.open(VERSION).then((c) => c.put(req, copy)) }
        return res
      }))
    )
  }
})
