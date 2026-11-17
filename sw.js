/* Service worker: la app abre sin internet con los últimos datos vistos.
   Si cambias index.html o hero3d.js, sube V para que los celulares bajen lo nuevo. */
const V = "usdcop-v1";
const SHELL = ["./", "index.html", "hero3d.js", "manifest.webmanifest", "icons/icon-192.png", "icons/icon-512.png",
  "https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js",
  "https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/ScrollTrigger.min.js",
  "https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"];
self.addEventListener("install", e => { e.waitUntil(caches.open(V).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== V).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", e => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET") return;
  // datos: primero la red (siempre lo más nuevo), si no hay internet, lo guardado
  if (u.pathname.includes("/data/")) {
    e.respondWith(fetch(e.request).then(r => { const cp = r.clone(); caches.open(V).then(c => c.put(e.request, cp)); return r; }).catch(() => caches.match(e.request, { ignoreSearch: true })));
    return;
  }
  e.respondWith(caches.match(e.request).then(hit => hit || fetch(e.request).then(r => { if (r.ok && (u.origin === location.origin || u.hostname === "cdnjs.cloudflare.com" || u.hostname.includes("gstatic") || u.hostname.includes("googleapis"))) { const cp = r.clone(); caches.open(V).then(c => c.put(e.request, cp)); } return r; })));
});
