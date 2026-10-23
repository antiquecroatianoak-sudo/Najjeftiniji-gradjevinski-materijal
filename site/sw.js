// Omogućuje da se aplikacija otvori i bez interneta (s posljednjim cijenama).
// Isti origin (github.io) dijele i druge aplikacije: ovaj worker dira samo vlastite cacheove (prefiks "gradjevina-")
// i samo zahtjeve unutar vlastitog opsega (scope).
const PREFIKS = "gradjevina-";
const CACHE = PREFIKS + "v15";
const OSNOVA = ["./", "index.html", "stil.css", "aplikacija.js", "skupine.js", "manifest.webmanifest", "ikona.svg", "ikona-192.png", "ikona-512.png"];

// Cjenik se pri prvom posjetu dohvati prije nego worker preuzme stranicu, pa ga se sprema i ovdje: aplikacija se tada
// otvara bez interneta s posljednjim cijenama već nakon prvog posjeta. Nedostupan cjenik ne ruši instalaciju.
const PODACI = ["data/proizvodi.json", "data/skupine.json", "data/dostava.json"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(OSNOVA)
    .then(() => Promise.all(PODACI.map((u) => c.add(u).catch(() => {}))))));
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((k) => Promise.all(k.filter((x) => x.startsWith(PREFIKS) && x !== CACHE).map((x) => caches.delete(x)))));
  e.waitUntil(self.clients.claim());
});

function uOpsegu(url) { return url.startsWith(self.registration.scope); }

// Uvijek prvo pokušaj s interneta (svježe cijene), a ako nema veze, koristi spremljeno iz vlastitog cachea.
self.addEventListener("fetch", (e) => {
  if (e.request.method !== "GET" || !uOpsegu(e.request.url)) return;
  e.respondWith(
    fetch(e.request)
      .then((odgovor) => {
        if (odgovor.ok) {
          const kopija = odgovor.clone();
          e.waitUntil(caches.open(CACHE).then((c) => c.put(e.request, kopija)).catch(() => {}));
        }
        return odgovor;
      })
      .catch(async () => (await (await caches.open(CACHE)).match(e.request, { ignoreSearch: true }))
        || new Response("Nema internetske veze.", { status: 503, headers: { "Content-Type": "text/plain; charset=utf-8" } }))
  );
});
