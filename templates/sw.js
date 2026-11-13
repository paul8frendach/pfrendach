/* Oasis Media Visions service worker.
   Conservative on purpose: hashed static assets are cached (immutable, so
   never stale), navigations always go to the network first and only fall back
   to a cached home shell when offline. Bump CACHE to invalidate. */
const CACHE = "omv-v2";
const OFFLINE_URL = "/";

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((c) => c.add(OFFLINE_URL)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // Hashed static assets — cache-first, they never change under a given URL.
  if (url.pathname.startsWith("/static/")) {
    event.respondWith(caches.open(CACHE).then(async (cache) => {
      const hit = await cache.match(req);
      if (hit) return hit;
      const res = await fetch(req);
      if (res && res.ok) cache.put(req, res.clone());
      return res;
    }));
    return;
  }

  // Page navigations — network first, cached home as the offline fallback only.
  if (req.mode === "navigate") {
    event.respondWith((async () => {
      try {
        return await fetch(req);
      } catch (err) {
        return (await caches.match(OFFLINE_URL)) || Response.error();
      }
    })());
  }
});
