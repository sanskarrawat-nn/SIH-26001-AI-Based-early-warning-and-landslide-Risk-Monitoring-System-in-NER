importScripts('/outbox.js');
const CACHE = 'ner-shell-__BUILD__';
const SHELL = __PRECACHE__;
self.addEventListener('install', event => event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(SHELL))));
// Let an existing session finish; the new shell activates when the old app closes.
self.addEventListener('activate', event => event.waitUntil((async () => {
  for (const name of await caches.keys()) if (name.startsWith('ner-shell-') && name !== CACHE) await caches.delete(name);
  await self.clients.claim();
})()));
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || url.origin !== self.location.origin || url.pathname.startsWith('/api/')) return;
  if (event.request.mode === 'navigate') {
    event.respondWith(fetch(event.request).catch(async () => (await caches.open(CACHE)).match('/index.html')));
  } else if (SHELL.includes(url.pathname)) {
    event.respondWith(caches.match(event.request).then(cached => cached || fetch(event.request)));
  }
});
self.addEventListener('sync', event => {
  if (event.tag === 'ner-field-reports') event.waitUntil((async () => {
    try { await self.NEROutbox.sync(); }
    finally { for (const client of await self.clients.matchAll()) client.postMessage({type: 'ner-outbox-changed'}); }
  })());
});
