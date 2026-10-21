// Kombinirani filtri trgovina, „jedna trgovina“, listanje ponuda i prikaz trgovina iznad 8, s nerazvrstanim artiklima.
// Sintetički cjenik s nazivima kakve imaju stvarni cjenici (nisu stvarne cijene): node tests/filtri.cjs
const assert = require("node:assert/strict");
const ucitaj = require("../scripts/aplikacija-vm.cjs");

const lanci = Array.from({ length: 12 }, (_, i) => `T${i + 1}`);
const P = (naziv, iznos, jedinica, cijene) => [naziv, iznos ? `${iznos} ${jedinica}` : "", iznos, jedinica, 0, cijene, "", null];
const proizvodi = [
  P("Cement CEM II/B-M (LL-V) 42,5 N 25 kg", 25, "kg", lanci.flatMap((_, l) => [l, 6 + ((l * 7) % 12) / 10])),
  P("CEMENT 25KG ALPACEM 42,5N", 25, "kg", [1, 6.4]),
  P("Kanta za cement 12 l", 12, "l", [2, 3.0]),                           // nije cement, ali je moguće podudaranje
  P("Kobaltno svrdlo za metal 1 mm, HSS-CO", 0, "", [4, 2.1, 5, 2.0]),     // nerazvrstano
  P("MATICA M-  6 DIN934317 6", 0, "", [6, 0.1]),                          // nerazvrstano
  P("Imbus ključ 3 mm", 0, "", [7, 1.5, 8, 1.4]),                          // nerazvrstano
  P("ORSO ARBOR boja 1 l", 1, "l", [9, 12]),                               // nepoznata riječ prije pojma
  P("Boja za zidove bijela 15 l", 15, "l", [9, 30, 10, 28]),
  P("Profil UD 28 3 m", 3, "m", [1, 2.5]),                                 // nerazvrstano, riječ na početku
  P("R CW profil 50 4000 mm", 4, "m", [2, 4.1]),                           // nerazvrstano, riječ u sredini
  P("Bi-metalna pila za rupe 19 mm", 0, "", [3, 9.9]),
  P("Metalna pila 300 mm", 0, "", [4, 7.5]),
  P("Set kistova 3 kom", 0, "", [5, 4.2]),                                 // pribor/set: nerazvrstano
  P("Kist ravni 50 mm", 0, "", [6, 2.2]),
  P("List kružne pile 210 mm", 0, "", [7, 9.9]),                           // razvrstano (list-pile)
  P("List za pilu", 0, "", [8, 3.1]),                                      // nerazvrstano: riječi nisu uzastopne
];
const lanciKojiImaju = (i) => new Set(proizvodi[i][5].filter((_, k) => k % 2 === 0));
const app = ucitaj({ datum: "2026-10-21", lanci, vrsteIzvora: lanci.map(() => "trgovina"), proizvodi });
const A = app.__api;
const kombinacije = [[[], null], ...lanci.map((l) => [lanci.filter((x) => x !== l), null]), ...lanci.map((l) => [[l], null]),
  ...lanci.map((l) => [[], l]), [["T1", "T4"], null], [["T1", "T2", "T3", "T4"], "T12"]];
// Očekivanje je zapisano ručno (ne iz klasifikatora): koje proizvode upit mora moći prikazati.
const ocekivano = { "cement": [0, 1, 2], "boja": [6, 7], "kobaltno svrdlo": [3], "matica": [4], "imbus ključ": [5],
  "profil": [8, 9], "metalna pila": [10, 11], "kist": [12, 13], "list pilu": [14, 15] };
for (const [upit, indeksi] of Object.entries(ocekivano)) {
  for (const [iskljuceni, jedna] of kombinacije) {
    app.__filtar(iskljuceni, jedna);
    const dopusteni = A.dozvoljeniLanci();
    const ponude = A.ponudeZaGrupu(upit, dopusteni);
    const ocek = indeksi.filter((i) => [...lanciKojiImaju(i)].some((l) => dopusteni.has(l)));
    assert.deepEqual(Array.from(ponude, (p) => p.i).sort(), [...ocek].sort(), `${upit} · bez ${iskljuceni} · jedna ${jedna}`);
    assert(ponude.every((p) => dopusteni.has(p.lanac)), "offer only from an allowed store");
    for (const p of ponude) {
      const naj = Math.min(...proizvodi[p.i][5].filter((_, k) => k % 2 === 0).map((l, k) => [l, proizvodi[p.i][5][2 * k + 1]])
        .filter(([l]) => dopusteni.has(l)).map(([, c]) => c));
      assert.equal(p.cijena, naj, "cheapest allowed store for each product");
    }
  }
}
app.__filtar([], null);
// Nerazvrstani artikli nisu najpovoljniji i nisu rangirani po jedinici, ali su dostupni.
assert(!A.ponudeZaGrupu("boja", A.dozvoljeniLanci()).find((p) => p.i === 6).vrstaNejasna, "brand before the noun: still paint");
assert(A.ponudeZaGrupu("kist", A.dozvoljeniLanci()).find((p) => p.i === 12).vrstaNejasna, "a set is not classified as a brush");
assert(!A.imaJedinicnu(A.ponudeZaGrupu("cement", A.dozvoljeniLanci()).find((p) => p.i === 2)), "bucket is not ranked as cement");
// Listanje: „Sljedeći“ obilazi sve ponude i vraća se na prvu.
app.vm = require("vm");
require("vm").runInContext(`
  stanje.popis = [{ naziv: "cement", kom: 1 }];
  prikaziRezultate = () => {}; spremi = () => {};
  const n = ponudeZaGrupu("cement").length, vidjeno = new Set([0]);
  for (let k = 0; k < n; k++) { promijeni("cement", +1); vidjeno.add(stanje.odabir.cement); }
  if (vidjeno.size !== n || stanje.odabir.cement !== 0) throw new Error("listanje ne obilazi sve ponude");
  promijeni("cement", -1); if (stanje.odabir.cement !== n - 1) throw new Error("natrag s prve ide na zadnju");
`, app);
// Sve u jednom dućanu: svih 12 trgovina vidljivo odmah, bez dodatnog klika i bez ograničenja na 8.
require("vm").runInContext(`
  const cvor = () => ({ children: [], hidden: false, textContent: "", className: "", set innerHTML(v) { this.children = []; },
    appendChild(c) { this.children.push(c); }, append(...c) { this.children.push(...c); }, setAttribute() {} });
  const cvorovi = {};
  document.getElementById = (id) => cvorovi[id] || (cvorovi[id] = cvor());
  document.createElement = () => cvor();
  stanje.popis = [{ naziv: "cement", kom: 1 }];
  stanje.jedna = null; stanje.iskljuceni = []; ponudeCache.clear();
  stanje.odabir = {}; stanje.odabirSvi = {};
  globalThis.__rez = prikaziJednuTrgovinu();
  globalThis.__redova = cvorovi["trgovine-usporedba"].children.length;
`, app);
assert.equal(app.__rez.potpune.length, 12, "every store with the item is listed");
assert.equal(app.__redova, 12, "all rows rendered immediately");
console.log(`FILTER PASS: ${Object.keys(ocekivano).length} queries × ${kombinacije.length} store filters, cheapest allowed store, ` +
  `unclassified reachable and unranked, offer paging wraps, all ${app.__redova} stores listed at once`);
