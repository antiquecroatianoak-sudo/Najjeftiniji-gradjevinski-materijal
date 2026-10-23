// Stvarni test u pregledniku (Chromium, Playwright): obje aplikacije na ISTOM originu i točnim putanjama
// /Najjeftinija-kosarica/ i /Najjeftiniji-gradjevinski-materijal/ (kao na github.io).
//  - nadogradnja starog građevinskog service workera (gradjevina-v14) na novi; aktivacija u oba redoslijeda;
//  - tuđi (kosarica-*) i nepovezani cacheovi ostaju; zasebni localStorage popisi; offline otvaranje obiju aplikacija;
//  - vlastiti scope i offline zamjena (tuđi resurs se ne poslužuje iz tuđeg cachea);
//  - mobilno 320 i 390 px: firme, cijeli popis, Bez dostave / S dostavom, promjena adrese, nepotpune ponude;
//    nepoznata dostava = „Dostava na upit”, nikad 0 € ni potvrđen najjeftiniji konačni iznos; nijedan zahtjev izvan origina.
//
// node tests/preglednik.cjs --kosarica DIR --stari DIR --novi DIR [--izlaz DIR]
//   DIR su mape s datotekama stranice (site/). Ako u mapi nema data/proizvodi.json, poslužuje se SINTETIČKI cjenik iz
//   ovog testa (nije stvaran; samo za lokalno pokretanje bez mreže). U GitHub Actions --novi je site/ sa stvarnim uvozom.
const fs = require("fs");
const http = require("http");
const path = require("path");
const assert = require("node:assert/strict");

function nadjiPlaywright() {
  for (const p of ["playwright", "/opt/node22/lib/node_modules/playwright"]) {
    try { return require(p); } catch (e) { /* sljedeći */ }
  }
  throw new Error("Playwright nije instaliran (npm i playwright)");
}
const { chromium } = nadjiPlaywright();

const arg = (ime, zadano) => { const i = process.argv.indexOf("--" + ime); return i > 0 ? process.argv[i + 1] : zadano; };
const KOS = path.resolve(arg("kosarica"));
const STARI = path.resolve(arg("stari"));
const NOVI = path.resolve(arg("novi"));
const IZLAZ = path.resolve(arg("izlaz", "preglednik-dokazi"));
fs.mkdirSync(IZLAZ, { recursive: true });
const K = "/Najjeftinija-kosarica/";
const G = "/Najjeftiniji-gradjevinski-materijal/";

// Sintetički cjenici (samo kad stvarnih nema): jasno označeni, ne ulaze u repozitorij ni aplikaciju.
const SINT_G = {
  datum: "2026-10-23", verzija: 2, sinteticki: true,
  lanci: ["Gavroprom", "Top Alati · Zagreb", "Top Alati · Split", "Profi baucentar"],
  firmeLanaca: ["Gavroprom", "Top Alati", "Top Alati", "Profi baucentar"],
  vrsteIzvora: ["trgovina", "trgovina", "trgovina", "trgovina"],
  proizvodi: [
    ["Cement CEM II 25 kg", "25 kg", 25, "kg", 0, [0, 6.2, 1, 6.9, 2, 6.5, 3, 7.1], "", null],
    ["Ljepilo za pločice C2TE 25 kg", "25 kg", 25, "kg", 0, [0, 11.4, 1, 10.9, 3, 12.5], "", null],
    ["Gips ploča 12,5 mm 2,6 m2", "2,6 m2", 2.6, "m2", 0, [1, 8.9, 3, 9.4], "", null],
  ],
};
const SINT_K = {
  datum: "2026-10-22", verzija: 2, sinteticki: true, lanci: ["Konzum", "Lidl"],
  proizvodi: [["Mlijeko 2,8% 1 l", "1 l", 1, "l", 0, [0, 1.19, 1, 1.09], [null, null], -1]],
};

let gradjevinska = STARI; // koju verziju građevinske aplikacije poslužitelj trenutno daje
const tipovi = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".json": "application/json",
  ".svg": "image/svg+xml", ".png": "image/png", ".webmanifest": "application/manifest+json" };
const zahtjevi = [];
function datoteka(korijen, rel, rezerva) {
  let f = path.join(korijen, rel || "index.html");
  if (fs.existsSync(f) && fs.statSync(f).isDirectory()) f = path.join(f, "index.html");
  if (fs.existsSync(f)) return fs.readFileSync(f);
  if (rel === "data/proizvodi.json") return rezerva ? Buffer.from(JSON.stringify(rezerva)) : null;
  return null;
}
const posluzitelj = http.createServer((req, res) => {
  const url = decodeURIComponent(req.url.split("?")[0]);
  zahtjevi.push(url);
  let tijelo = null;
  if (url.startsWith(K)) tijelo = datoteka(KOS, url.slice(K.length), SINT_K);
  else if (url.startsWith(G)) {
    const rel = url.slice(G.length);
    // Stara verzija nema svoje podatke u ovom testu: dijeli data/ s novom (isti oblik cjenika).
    tijelo = datoteka(gradjevinska, rel, null) || (rel.startsWith("data/") ? datoteka(NOVI, rel, SINT_G) : null);
  }
  if (!tijelo) { res.writeHead(404); return res.end("404"); }
  res.writeHead(200, { "Content-Type": tipovi[path.extname(url)] || (url.endsWith("/") ? tipovi[".html"] : "application/octet-stream"),
    "Cache-Control": "no-cache" });
  res.end(tijelo);
});

const dokazi = [];
const zabiljezi = (s) => { dokazi.push(s); console.log("  ✓ " + s); };

async function main() {
  await new Promise((r) => posluzitelj.listen(0, "127.0.0.1", r));
  const PORT = posluzitelj.address().port;
  const ORIGIN = `http://127.0.0.1:${PORT}`;
  const ugasi = () => new Promise((r) => { posluzitelj.close(r); posluzitelj.closeAllConnections(); });
  const upali = () => new Promise((r) => posluzitelj.listen(PORT, "127.0.0.1", r));
  const opcije = { headless: true };
  // PREGLEDNIK: putanja do Chromea/Chromiuma (u GitHub Actions instalirani Google Chrome slike runnera).
  const putanja = process.env.PREGLEDNIK || (fs.existsSync("/opt/pw-browsers/chromium") ? "/opt/pw-browsers/chromium" : "");
  if (putanja) opcije.executablePath = putanja;
  const preglednik = await chromium.launch(opcije);
  console.log(`Chromium ${preglednik.version()}, origin ${ORIGIN}`);
  const realanG = fs.existsSync(path.join(NOVI, "data", "proizvodi.json"));
  const realanK = fs.existsSync(path.join(KOS, "data", "proizvodi.json"));
  console.log(`Cjenik građevinske: ${realanG ? "STVARNI uvoz" : "sintetički"}; Košarice: ${realanK ? "stvarni" : "sintetički"}`);

  const imena = (p) => p.evaluate(() => caches.keys().then((k) => k.sort()));
  // Čeka (u Node petlji) da je u opsegu stranice AKTIVIRAN worker bez čekajućeg/instalirajućeg i da postoji njegov cache.
  async function aktivan(page, cache, opseg) {
    let st;
    for (let i = 0; i < 100; i++) {
      st = await page.evaluate(async (o) => {
        const r = await navigator.serviceWorker.getRegistration(o);
        return { stanje: r && r.active && r.active.state, ceka: !!(r && (r.waiting || r.installing)),
          kontrolira: !!navigator.serviceWorker.controller, cacheovi: await caches.keys() };
      }, opseg || page.url());
      if (st.stanje === "activated" && !st.ceka && st.kontrolira && st.cacheovi.includes(cache)) return st;
      await page.waitForTimeout(300);
    }
    throw new Error(`${cache} nije aktivan: ${JSON.stringify(st)}`);
  }
  async function dodaj(page, tekst) {
    await page.fill("#unos", tekst);
    await page.press("#unos", "Enter");
  }
  const sw = (p) => p.evaluate(async () => (await navigator.serviceWorker.getRegistration()).active.scriptURL);

  // ---- 1) Nadogradnja: stari građevinski SW (v14) aktivan, zatim Košarica i nepovezani cache, pa nova verzija.
  {
    gradjevinska = STARI;
    const ctx = await preglednik.newContext();
    const g = await ctx.newPage();
    await g.goto(ORIGIN + G);
    await aktivan(g, "gradjevina-v14");
    await dodaj(g, "3 vreće cementa");
    const k = await ctx.newPage();
    await k.goto(ORIGIN + K);
    await aktivan(k, "kosarica-v34");
    await dodaj(k, "mlijeko");
    await k.evaluate(() => caches.open("nepovezan-cache").then((c) => c.put("/nepovezano.txt", new Response("x"))));
    assert.deepEqual(await imena(k), ["gradjevina-v14", "kosarica-v34", "nepovezan-cache"]);
    gradjevinska = NOVI;
    await g.reload();
    const t0 = Date.now();
    await aktivan(g, "gradjevina-v15");
    const trajanje = Date.now() - t0;
    assert.deepEqual(await imena(g), ["gradjevina-v15", "kosarica-v34", "nepovezan-cache"]);
    // Ponovno otvaranje pod novom verzijom: stari cache se ne vraća, popis ostaje.
    await g.reload();
    await aktivan(g, "gradjevina-v15");
    await g.waitForSelector("#kartice li");
    assert.match(await g.textContent("#kartice"), /cement/i);
    assert.deepEqual(await imena(g), ["gradjevina-v15", "kosarica-v34", "nepovezan-cache"]);
    assert.match(await sw(g), /Najjeftiniji-gradjevinski-materijal\/sw\.js$/);
    assert.match(await sw(k), /Najjeftinija-kosarica\/sw\.js$/);
    zabiljezi(`nadogradnja v14 → v15 (aktivirana za ${trajanje} ms nakon ponovnog otvaranja): obrisan samo gradjevina-v14; popis ostaje; kosarica-v34 i nepovezan-cache ostaju; svaka aplikacija ima svoj SW`);
    await ctx.close();
  }

  // ---- 2) Aktivacija u oba redoslijeda (nova verzija), zasebni popisi, offline i scope.
  gradjevinska = NOVI;
  for (const redoslijed of [[G, K], [K, G]]) {
    const ctx = await preglednik.newContext();
    const prva = await ctx.newPage();
    await prva.goto(ORIGIN + redoslijed[0]);
    await aktivan(prva, redoslijed[0] === G ? "gradjevina-v15" : "kosarica-v34");
    await prva.evaluate(() => caches.open("nepovezan-cache").then((c) => c.put("/nepovezano.txt", new Response("x"))));
    const druga = await ctx.newPage();
    await druga.goto(ORIGIN + redoslijed[1]);
    await aktivan(druga, redoslijed[1] === G ? "gradjevina-v15" : "kosarica-v34");
    assert.deepEqual(await imena(druga), ["gradjevina-v15", "kosarica-v34", "nepovezan-cache"]);
    const [g, k] = redoslijed[0] === G ? [prva, druga] : [druga, prva];
    await dodaj(g, "20 m2 laminata");
    await dodaj(k, "kruh");
    const spremiste = await g.evaluate(() => ({ g: JSON.parse(localStorage.getItem("gradjevina-v1")),
      k: JSON.parse(localStorage.getItem("kosarica-v1")) }));
    assert.ok(/laminat/i.test(spremiste.g.popis[0].naziv) && spremiste.g.popis.length === 1, JSON.stringify(spremiste.g));
    assert.ok(/kruh/i.test(spremiste.k.popis[0].naziv) && spremiste.k.popis.length === 1, JSON.stringify(spremiste.k));
    const naziv = redoslijed[0] === G ? "građevinska pa Košarica" : "Košarica pa građevinska";
    zabiljezi(`${naziv}: oba SW aktivna, svi cacheovi ostaju; popisi zasebni (gradjevina-v1: laminat, kosarica-v1: kruh)`);

    // Offline: poslužitelj ne odgovara (mreža pada), obje aplikacije se otvaraju iz vlastitog cachea s popisom.
    // Stvarni prekid: poslužitelj prestaje slušati (context.setOffline u Chromiumu ne vrijedi za zahtjeve service workera).
    await ugasi();
    await g.reload();
    await k.reload();
    await g.waitForSelector("#kartice li");
    await k.waitForSelector("#kartice li");
    assert.match(await g.textContent("#kartice"), /laminat/i);
    assert.match(await k.textContent("#kartice"), /kruh/i);
    assert.equal(await g.title(), "Najjeftiniji građevinski materijal");
    // Vlastiti scope: tuđi resurs se ne poslužuje iz tuđeg cachea; nepostojeći vlastiti resurs = vlastita zamjena (503).
    const tudji = await g.evaluate(() => fetch("/Najjeftinija-kosarica/stil.css").then((r) => r.status, () => "mreža"));
    const vlastiti = await g.evaluate(() => fetch("nepostojece.txt").then(async (r) => [r.status, await r.text()], () => "mreža"));
    assert.equal(tudji, "mreža", "construction SW must not serve Košarica's cached file");
    assert.deepEqual(vlastiti, [503, "Nema internetske veze."]);
    const statusG = await g.textContent("#status");
    const statusK = (await k.textContent("#status")).trim();
    assert.match(statusG, /Cijene od/, "offline after first visit opens with the last cached prices");
    zabiljezi(`${naziv} offline: obje aplikacije otvorene iz vlastitog cachea s popisom; tuđi resurs nije poslužen; vlastita zamjena 503 (građevinska: ${statusG.trim().slice(0, 80)}; Košarica: ${statusK.slice(0, 80)})`);
    await g.screenshot({ path: path.join(IZLAZ, `offline-gradjevinska-${redoslijed[0] === G ? "prva" : "druga"}.png`) });
    await ctx.close();
    await upali();
  }

  // ---- 3) Mobilno 320 / 390 px, nova verzija, sav promet samo na isti origin.
  for (const sirina of [320, 390]) {
    const ctx = await preglednik.newContext({ viewport: { width: sirina, height: 800 }, isMobile: true, hasTouch: true });
    const p = await ctx.newPage();
    const vanjski = [];
    p.on("request", (r) => { if (!r.url().startsWith(ORIGIN)) vanjski.push(r.url()); });
    await p.goto(ORIGIN + G);
    await p.waitForFunction(() => /firmi|trgovin/i.test(document.getElementById("status").textContent)
      && !/Učitavam/.test(document.getElementById("status").textContent), null, { timeout: 60000 })
      .catch(async (e) => { throw new Error(`status: ${await p.textContent("#status")}`); });
    const status = (await p.textContent("#status")).trim();
    for (const t of ["3 vreće cementa", "2 vreće ljepila za pločice", "10 m2 gips ploča", "5 kg vijaka za gips"]) await dodaj(p, t);
    await p.waitForFunction(() => document.querySelectorAll("#kartice li").length === 4);
    // Mjeri se prema zadanoj širini zaslona: mobilni Chromium širi vizualni prikaz na širinu sadržaja, pa innerWidth to skriva.
    const preljev = () => p.evaluate((w) => Math.max(document.documentElement.scrollWidth, document.body.scrollWidth) - w, sirina);
    assert.ok(await preljev() <= 0, `horizontal overflow ${await preljev()} px at ${sirina}`);
    const bez = (await p.textContent("#jedna-trgovina")).replace(/\s+/g, " ");
    await p.screenshot({ path: path.join(IZLAZ, `mobilno-${sirina}-bez-dostave.png`), fullPage: true });

    await p.click("#s-dostavom");
    assert.equal(await p.isVisible("#adresa-dostave"), true);
    let s = (await p.textContent("#jedna-trgovina")).replace(/\s+/g, " ");
    assert.doesNotMatch(s, /dostava 0,00 €|\+ 0,00 €/, "unknown delivery never 0 €");
    await p.fill("#adresa-postanski", "10000");
    await p.fill("#adresa-mjesto", "Zagreb");
    s = (await p.textContent("#jedna-trgovina")).replace(/\s+/g, " ");
    const s2 = await p.evaluate(() => { const i = document.getElementById("adresa-postanski"); i.value = "21000";
      i.dispatchEvent(new Event("input", { bubbles: true })); return document.getElementById("jedna-trgovina").textContent.replace(/\s+/g, " "); });
    const spremljeno = await p.evaluate(() => JSON.parse(localStorage.getItem("gradjevina-v1")));
    assert.equal(spremljeno.adresa.postanski, "21000");
    assert.equal(spremljeno.popis.length, 4, "address change keeps the list");
    for (const t of [s, s2]) {
      assert.doesNotMatch(t, /dostava 0,00 €|\+ 0,00 €/, "unknown delivery never 0 €");
      // Bez nijedne objavljene fiksne cijene dostave nema potvrđenog konačnog iznosa s dostavom.
      if (!/materijal [\d.,]+ € \+ dostava [\d.,]+ €/.test(t)) assert.match(t, /na upit/i);
    }
    assert.ok(await preljev() <= 0, `horizontal overflow with delivery at ${sirina}`);
    await p.screenshot({ path: path.join(IZLAZ, `mobilno-${sirina}-s-dostavom.png`), fullPage: true });
    const nepotpune = await p.isVisible("#nepotpune-naslov");
    assert.deepEqual(vanjski, [], "no request leaves the origin (nothing sent to traders)");
    zabiljezi(`${sirina} px: ${status}; 4 stavke; bez vodoravnog preljeva; S dostavom bez adrese i s 10000/21000 → „na upit”, nikad 0 €; ` +
      `popis i adresa ostaju samo u localStorageu; nepotpune ${nepotpune ? "prikazane" : "nema"}; 0 zahtjeva izvan origina`);
    fs.writeFileSync(path.join(IZLAZ, `mobilno-${sirina}.txt`), `${status}\n\nBEZ DOSTAVE:\n${bez}\n\nS DOSTAVOM 10000:\n${s}\n\nS DOSTAVOM 21000:\n${s2}\n`);
    console.log(`--- ${sirina} px, S dostavom 21000 (izvadak):\n${s2.slice(0, 900)}`);
    await ctx.close();
  }

  await preglednik.close();
  posluzitelj.close();
  fs.writeFileSync(path.join(IZLAZ, "rezultat.txt"), dokazi.join("\n") + "\n");
  console.log("BROWSER PASS: " + dokazi.length + " provjera; dokazi u " + IZLAZ);
}
main().catch((e) => { console.error(e); posluzitelj.close(); process.exit(1); });
