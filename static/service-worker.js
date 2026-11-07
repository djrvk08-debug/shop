const CACHE_NAME = "dharti-fresh-v1";
const APP_SHELL = [
  "/",
  "/static/manifest.json",
  "/static/css/tokens.css",
  "/static/css/base.css",
  "/static/css/components.css",
  "/static/css/store.css",
  "/static/js/main.js",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;

  const requestUrl = new URL(event.request.url);
  if (requestUrl.origin !== self.location.origin) return;

  if (requestUrl.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.match(event.request).then(
        (cachedResponse) =>
          cachedResponse ||
          fetch(event.request).then((response) => {
            const responseCopy = response.clone();
            caches.open(CACHE_NAME).then((cache) =>
              cache.put(event.request, responseCopy)
            );
            return response;
          })
      )
    );
    return;
  }

  event.respondWith(
    fetch(event.request).catch(() => caches.match("/"))
  );
});