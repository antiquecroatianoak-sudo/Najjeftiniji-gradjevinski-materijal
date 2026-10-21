// Revizija puta uvoz → klasifikacija → pretraga na stvarnom cjeniku: node scripts/revizija.cjs [site/data/proizvodi.json]
// Za svaku vrstu provjerava da upit njezinim nazivom (i inačicama velikih slova i bez dijakritike) vraća sve članove,
// broji nerazvrstane po izvoru s primjerima. Ništa se ne briše; izvještaj -> site/data/revizija.json.
const fs = require("fs");
const path = require("path");
const Skupine = require("../site/skupine.js");

const ulaz = process.argv[2] || path.join(__dirname, "..", "site", "data", "proizvodi.json");
const podaci = JSON.parse(fs.readFileSync(ulaz, "utf8"));
const g = Skupine.pripremi(podaci.proizvodi);
const bezDijakritike = (s) => s.replace(/đ/g, "d").replace(/Đ/g, "D").normalize("NFD").replace(/[̀-ͯ]/g, "");

const poIzvoru = podaci.lanci.map((naziv) => ({ naziv, ponuda: 0, razvrstano: 0, nerazvrstano: 0, primjeri: [] }));
podaci.proizvodi.forEach((p, i) => {
  const vrsta = g.vrstaProizvoda(i);
  for (let k = 0; k < p[5].length; k += 2) {
    const s = poIzvoru[p[5][k]];
    s.ponuda++;
    if (vrsta) s.razvrstano++;
    else { s.nerazvrstano++; if (s.primjeri.length < 8) s.primjeri.push(p[0]); }
  }
});

const vrste = [];
const gubici = [];
for (const d of Skupine.definicije) {
  const clanovi = g.katalog.find((k) => k.id === d.id)?.indeksi || [];
  const osnovni = Skupine.nazivi[d.id][0]; // naziv kakav korisnik upisuje
  const upiti = [osnovni, osnovni.toUpperCase(), bezDijakritike(osnovni), osnovni[0].toUpperCase() + osnovni.slice(1)];
  for (const u of upiti) {
    const nadjeno = new Set([...(g.pogoci(u) || []), ...g.moguciPogoci(u)]);
    const nedostaje = clanovi.filter((i) => !nadjeno.has(i));
    if (nedostaje.length) gubici.push({ vrsta: d.id, upit: u, nedostaje: nedostaje.length, primjeri: nedostaje.slice(0, 5).map((i) => podaci.proizvodi[i][0]) });
  }
  vrste.push({ id: d.id, naziv: d.naziv, proizvoda: clanovi.length, mogucih: g.moguciPogoci(osnovni).length });
}

// ---- Pokrivenost po vrsti i izvoru, razlozi nerazvrstavanja ----
const razlozi = podaci.lanci.map(() => ({}));
const rijeciNerazvrstanih = new Map();
podaci.proizvodi.forEach((p, i) => {
  if (g.vrstaProizvoda(i)) return;
  const a = Skupine.analiziraj(p[0], p[4]);
  const r = a.razlog || "ostalo";
  for (let k = 0; k < p[5].length; k += 2) {
    const z = razlozi[p[5][k]][r] || (razlozi[p[5][k]][r] = { broj: 0, primjeri: [] });
    z.broj++;
    if (z.primjeri.length < 3) z.primjeri.push(p[0]);
  }
  const prva = a.rijeci.slice(Number(p[4]) || 0).find((w) => w.length >= 3 && !/^\d/.test(w));
  if (prva) rijeciNerazvrstanih.set(prva, (rijeciNerazvrstanih.get(prva) || 0) + 1);
});
const pokrivenost = Skupine.definicije.map((d) => {
  const clanovi = g.katalog.find((k) => k.id === d.id)?.indeksi || [];
  const moguci = g.moguciPogoci(Skupine.nazivi[d.id][0]);
  const poIzvoru = {};
  for (const [skup, oznaka] of [[clanovi, "razvrstano"], [moguci, "moguce"]]) for (const i of skup) {
    const c = podaci.proizvodi[i][5];
    for (let k = 0; k < c.length; k += 2) {
      const l = podaci.lanci[c[k]];
      (poIzvoru[l] || (poIzvoru[l] = { razvrstano: 0, moguce: 0 }))[oznaka]++;
    }
  }
  return { id: d.id, razvrstano: clanovi.length, moguce: moguci.length, poIzvoru };
});

// ---- Kombinirani filtri: ista funkcija kao u aplikaciji, prema neovisno izračunatom očekivanju ----
const app = require("./aplikacija-vm.cjs")(podaci);
const A = app.__api;
const lanciSvi = podaci.lanci.map((_, i) => i);
const kombinacije = [{ opis: "svi", iskljuceni: [] },
  ...lanciSvi.map((l) => ({ opis: `samo ${podaci.lanci[l]}`, iskljuceni: podaci.lanci.filter((_, j) => j !== l) })),
  ...lanciSvi.map((l) => ({ opis: `bez ${podaci.lanci[l]}`, iskljuceni: [podaci.lanci[l]] })),
  ...lanciSvi.map((l) => ({ opis: `jedna trgovina ${podaci.lanci[l]}`, iskljuceni: [], jedna: podaci.lanci[l] }))];
const filtriGubici = [];
// Riječi naziva nerazvrstanih proizvoda pripremaju se jednom (inače 74 vrste × svi proizvodi).
const nerazvrstaniIndeksi = podaci.proizvodi.map((_, i) => i).filter((i) => !g.vrstaProizvoda(i));
const rijeciNaziva = [];
for (const i of nerazvrstaniIndeksi) rijeciNaziva[i] = Skupine.analiziraj(podaci.proizvodi[i][0]).rijeci;
let filtriProvjera = 0;
for (const d of Skupine.definicije) {
  const upit = Skupine.nazivi[d.id][0];
  // Očekivano: razvrstani i mogući članovi te nerazvrstani proizvodi koji sadrže sve riječi upita
  // (aplikacija ih namjerno vraća kao „vrsta za provjeru“). Riječi se ovdje provjeravaju neovisno o aplikaciji.
  // Pravilo nastavaka i prijedloga je ono iz aplikacije (specifikacija „sadrži riječ“), a usporedba je neovisna.
  const nastavci = A.NASTAVCI;
  const kor = (w) => { const k = w.length >= 4 ? w.replace(/[aeiou]+$/, "") : w; return k.length < 3 ? w : k; };
  const rijeciUpita = Skupine.analiziraj(upit).rijeci.filter((w) => !A.PRIJEDLOZI.includes(w)).map(kor);
  const sadrziSve = (i) => rijeciNaziva[i].length && rijeciUpita.every((k) => rijeciNaziva[i].some((w) => w.startsWith(k) && nastavci.includes(w.slice(k.length))));
  const clanovi = new Set([...(g.pogoci(upit) || []), ...g.moguciPogoci(upit), ...nerazvrstaniIndeksi.filter(sadrziSve)]);
  for (const k of kombinacije) {
    app.__filtar(k.iskljuceni, k.jedna);
    const dopusteni = A.dozvoljeniLanci();
    const ocekivano = [...clanovi].filter((i) => { const c = podaci.proizvodi[i][5]; for (let j = 0; j < c.length; j += 2) if (dopusteni.has(c[j])) return true; return false; });
    const ponude = A.ponudeZaGrupu(upit, dopusteni);
    const dobiveno = new Set(ponude.map((p) => p.i));
    filtriProvjera++;
    const nedostaje = ocekivano.filter((i) => !dobiveno.has(i));
    const visak = [...dobiveno].filter((i) => !clanovi.has(i));
    const dvaput = ponude.length !== dobiveno.size;
    const krivLanac = ponude.filter((p) => !dopusteni.has(p.lanac)).length;
    if (nedostaje.length || visak.length || dvaput || krivLanac) filtriGubici.push({ vrsta: d.id, filtar: k.opis, nedostaje: nedostaje.length,
      visak: visak.length, dvaput, krivLanac, primjeri: nedostaje.slice(0, 3).map((i) => podaci.proizvodi[i][0]),
      primjeriViska: visak.slice(0, 3).map((i) => podaci.proizvodi[i][0]) });
  }
}
app.__filtar([], null);

// ---- Referentni skup: nerazvrstani proizvodi moraju ostati dohvatljivi upitom svojih riječi ----
const nerazvrstani = podaci.proizvodi.map((_, i) => i).filter((i) => !g.vrstaProizvoda(i));
const korak = Math.max(1, Math.floor(nerazvrstani.length / 1000));
const referentni = nerazvrstani.filter((_, j) => j % korak === 0).slice(0, 1000);
const nedohvatljivi = [];
for (const i of referentni) {
  const r = Skupine.analiziraj(podaci.proizvodi[i][0]).rijeci.filter((w) => w.length >= 3 && !/^\d/.test(w)).slice(0, 2);
  if (!r.length) continue;
  const upit = r.join(" ");
  if (!A.pogoci(upit).includes(i)) nedohvatljivi.push({ upit, naziv: podaci.proizvodi[i][0] });
}

const izvjestaj = { cjenik: podaci.datum, proizvoda: podaci.proizvodi.length, razvrstano: g.ukupno - g.nerazvrstano,
  nerazvrstano: g.nerazvrstano, poIzvoru, vrste, gubici, pokrivenost,
  razloziNerazvrstavanja: podaci.lanci.map((l, i) => ({ izvor: l, razlozi: razlozi[i] })),
  najcesceRijeciNerazvrstanih: [...rijeciNerazvrstanih].sort((a, b) => b[1] - a[1]).slice(0, 60),
  filtri: { kombinacija: kombinacije.length, provjera: filtriProvjera, gubici: filtriGubici },
  referentni: { provjereno: referentni.length, nedohvatljivi: nedohvatljivi.length, primjeri: nedohvatljivi.slice(0, 20) } };
fs.writeFileSync(path.join(path.dirname(ulaz), "revizija.json"), JSON.stringify(izvjestaj, null, 1));
console.log(`Revizija: ${izvjestaj.proizvoda} proizvoda, razvrstano ${izvjestaj.razvrstano}, nerazvrstano ${izvjestaj.nerazvrstano} (ostaju u pretrazi i označeni za provjeru)`);
for (const s of poIzvoru) console.log(`  ${s.naziv}: ${s.ponuda} ponuda, razvrstano ${s.razvrstano}, nerazvrstano ${s.nerazvrstano}` + (s.primjeri.length ? ` | npr. ${s.primjeri.slice(0, 3).join(" ; ")}` : ""));
for (const v of vrste) console.log(`  vrsta ${v.id}: ${v.proizvoda} proizvoda, ${v.mogucih} mogućih za provjeru`);
for (const r of izvjestaj.razloziNerazvrstavanja) console.log(`  razlozi ${r.izvor}: ` + Object.entries(r.razlozi).map(([k, v]) => `${k} ${v.broj} (npr. ${v.primjeri[0]})`).join(" ; "));
console.log("  najčešće prve riječi nerazvrstanih: " + izvjestaj.najcesceRijeciNerazvrstanih.slice(0, 40).map(([w, n]) => `${w} ${n}`).join(", "));
console.log(gubici.length ? `GUBICI u pretrazi: ${JSON.stringify(gubici)}` : "Pretraga: nijedan razvrstan proizvod ne nestaje (naziv, VELIKA slova, bez dijakritike)");
console.log(filtriGubici.length ? `GUBICI u filtrima: ${JSON.stringify(filtriGubici.slice(0, 20))}`
  : `Filtri: ${filtriProvjera} provjera (${Skupine.definicije.length} vrsta × ${kombinacije.length} kombinacija trgovina), bez gubitka, viška ili dvostrukih ponuda`);
console.log(nedohvatljivi.length ? `Referentni skup: ${nedohvatljivi.length} od ${referentni.length} nerazvrstanih nedohvatljivo: ${JSON.stringify(nedohvatljivi.slice(0, 10))}`
  : `Referentni skup: svih ${referentni.length} nerazvrstanih (uzorak) dohvatljivo upitom svojih riječi`);
process.exitCode = gubici.length || filtriGubici.length || nedohvatljivi.length ? 1 : 0;
