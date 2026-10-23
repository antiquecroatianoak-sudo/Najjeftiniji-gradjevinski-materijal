// Bez dostave / S dostavom (6334670442, 6334674883, 6339768963): dostava za cijelu narudžbu samo iz objavljenog pravila
// firme, nepoznata dostava nikad 0 € ni najpovoljnija, područje i najmanja narudžba, besplatni prag, promjena adrese i
// načina čuva popis, točan optimum kombinacije s dostavom. Sintetički cjenik i pravila (nisu stvarni): node tests/dostava.cjs
const assert = require("node:assert/strict");
const vm = require("vm");
const ucitaj = require("../scripts/aplikacija-vm.cjs");

const PRAVILA = {
  A: { vrsta: "fiksno", iznos: 30, besplatno_od: 500, podrucje: { postanski: ["10"] }, url: "https://a.hr/dostava", provjereno: "2026-10-23" },
  B: { vrsta: "fiksno", iznos: 20, min_narudzba: 25, url: "https://b.hr/dostava", provjereno: "2026-10-23" },
  // C nema pravila: dostava na upit.
};
function scenarij(proizvodi, popis, pravila = PRAVILA) {
  const app = ucitaj({ datum: "2026-10-23", lanci: ["A", "B", "C"], vrsteIzvora: ["trgovina", "trgovina", "trgovina"], proizvodi });
  vm.runInContext(`
    const cvor = () => ({ children: [], hidden: false, textContent: "", className: "", value: "",
      classList: { add() {}, remove() {} }, set innerHTML(v) { this.children = []; },
      appendChild(c) { this.children.push(c); }, append(...c) { this.children.push(...c); }, setAttribute() {} });
    globalThis.__cvorovi = {};
    document.getElementById = (id) => __cvorovi[id] || (__cvorovi[id] = cvor());
    document.createElement = () => cvor();
    prikaziRezultate = () => {}; spremi = () => {};
    stanje.popis = ${JSON.stringify(popis)};
    dostava = { pravila: ${JSON.stringify(pravila)} };
  `, app);
  return app;
}
const run = (app, kod) => {
  const v = vm.runInContext(kod, app);
  return v && typeof v === "object" ? JSON.parse(JSON.stringify(v)) : v;
};
const P = (naziv, iznos, jedinica, cijene) => [naziv, `${iznos} ${jedinica}`, iznos, jedinica, 0, cijene, "", null];
// Cement 60 kg (3 × 25 kg): A 3 × 6 = 18, B 3 × 7 = 21, C 3 × 5 = 15. Ljepilo: A 10, B 9, C 8.
const proizvodi = [P("Cement CEM II 25 kg", 25, "kg", [0, 6, 1, 7, 2, 5]), P("Ljepilo za pločice C2TE 25 kg", 25, "kg", [0, 10, 1, 9, 2, 8])];
const popis = [{ naziv: "Cement", kom: 1, trazeno: { iznos: 60, jedinica: "kg" } }, { naziv: "Ljepilo za pločice", kom: 1 }];
const sazetak = (r) => r.potpune.map((x) => [x.ime, x.ukupno, x.konacno, x.najpovoljniji, x.dostava ? x.dostava.stanje : null]);

// 1) Zadano: Bez dostave, samo materijal (isti rezultat kao prije).
let app = scenarij(proizvodi, popis);
assert.equal(run(app, "stanje.dostava"), false, "default is without delivery");
let r = run(app, "prikaziJednuTrgovinu()");
assert.equal(r.dostava, undefined);
assert.deepEqual(r.potpune.map((x) => [x.ime, x.ukupno, x.najpovoljniji]), [["C", 23, true], ["A", 28, false], ["B", 30, false]]);

// 2) S dostavom bez poštanskog broja: sve na upit, nijedan konačni iznos, nema pobjednika ni nule.
run(app, "stanje.dostava = true");
r = run(app, "prikaziJednuTrgovinu()");
assert.ok(r.potpune.every((x) => x.konacno === null && !x.najpovoljniji && x.dostava.stanje === "na-upit"), JSON.stringify(sazetak(r)));
assert.equal(r.kombinacijaDostava, null);
assert.match(app.__cvorovi.kombinacija.textContent, /Sve kod jednog trgovca: nijedan potpuni trgovac nema poznatu dostavu/);
assert.match(app.__cvorovi["trgovine-usporedba"].children[0].children[0].children[1].textContent, /\+ dostava na upit/,
  "unknown delivery is shown as 'na upit', never as 0");

// 3) Zagreb 10000: A 28 + 30 = 58, B 30 + 20 = 50, C (najjeftiniji materijal 23) na upit -> nije pobjednik.
run(app, `stanje.adresa = { mjesto: "Zagreb", postanski: "10000", ulica: "" }`);
r = run(app, "prikaziJednuTrgovinu()");
assert.deepEqual(sazetak(r), [["B", 30, 50, true, "poznata"], ["A", 28, 58, false, "poznata"], ["C", 23, null, false, "na-upit"]]);
// Kombinacija s dostavom: dostava po narudžbi, ne po artiklu. A+B (cement A 18 + 30, ljepilo B 9 + 20 = 77) skuplje je
// od samog B (50); optimum je B, 1 trgovac.
assert.deepEqual([r.kombinacijaDostava.ukupno, r.kombinacijaDostava.trgovaca, r.kombinacijaDostava.dostave.map((d) => d.ime)], [50, 1, ["B"]]);
assert.match(app.__cvorovi.kombinacija.textContent, /Sve kod jednog trgovca: 50,00 € \(B: materijal 30,00 € \+ dostava 20,00 €; 1 dostava\)/);
assert.match(app.__cvorovi.kombinacija.textContent, /Samo materijal, bez dostave: 23,00 €/);

// 4) Split 21000: A izvan objavljenog područja -> na upit; B poznata.
run(app, `stanje.adresa = { mjesto: "Split", postanski: "21000", ulica: "" }`);
r = run(app, "prikaziJednuTrgovinu()");
assert.deepEqual(sazetak(r).map((x) => [x[0], x[4]]), [["B", "poznata"], ["C", "na-upit"], ["A", "na-upit"]], "address change recomputes availability");
assert.equal(run(app, "stanje.popis.length"), 2, "list kept");

// 5) Besplatni prag i najmanja narudžba: 1 vreća ljepila -> B ispod 25 € (na upit); A 10 + 30.
app = scenarij(proizvodi, [{ naziv: "Ljepilo za pločice", kom: 1 }]);
run(app, `stanje.dostava = true; stanje.adresa = { mjesto: "Zagreb", postanski: "10000", ulica: "" }`);
r = run(app, "prikaziJednuTrgovinu()");
assert.deepEqual(sazetak(r), [["A", 10, 40, true, "poznata"], ["C", 8, null, false, "na-upit"], ["B", 9, null, false, "na-upit"]]);
assert.match(r.potpune[2].dostava.opis, /ispod najmanjeg iznosa za dostavu \(25,00 €\)/);
app = scenarij(proizvodi, [{ naziv: "Ljepilo za pločice", kom: 60 }]);
run(app, `stanje.dostava = true; stanje.adresa = { mjesto: "Zagreb", postanski: "10000", ulica: "" }`);
r = run(app, "prikaziJednuTrgovinu()");
assert.deepEqual(sazetak(r).slice(0, 2), [["B", 540, 560, true, "poznata"], ["A", 600, 600, false, "poznata"]], "A free from 500 €");

// 6) Kombinacija dvaju trgovaca pobjeđuje kad je ušteda materijala veća od druge dostave; uspoređeno s potpunom pretragom.
const veliki = [P("Cement CEM II 25 kg", 25, "kg", [0, 5, 1, 9]), P("Ljepilo za pločice C2TE 25 kg", 25, "kg", [0, 20, 1, 9])];
app = scenarij(veliki, [{ naziv: "Cement", kom: 20 }, { naziv: "Ljepilo za pločice", kom: 10 }]);
run(app, `stanje.dostava = true; stanje.adresa = { mjesto: "Zagreb", postanski: "10000", ulica: "" }`);
r = run(app, "prikaziJednuTrgovinu()");
// A: 100 + 200 = 300 + 30 = 330; B: 180 + 90 = 270 + 20 = 290; A cement 100 + 30, B ljepilo 90 + 20 = 240.
assert.deepEqual(sazetak(r).map((x) => [x[0], x[2]]), [["B", 290], ["A", 330]]);
assert.deepEqual([r.kombinacijaDostava.ukupno, r.kombinacijaDostava.trgovaca], [240, 2]);
assert.match(app.__cvorovi.kombinacija.textContent, /2 zasebne dostave .* ušteda 50,00 €/);
// Potpuna pretraga svih dodjela stavki trgovcima s poznatom dostavom potvrđuje optimum.
let naj = Infinity;
for (const a of [0, 1]) for (const b of [0, 1]) {
  const nar = [0, 0];
  nar[a] += [100, 180][a];
  nar[b] += [200, 90][b];
  const d = nar.map((x, l) => (x ? (l === 0 ? (x >= 500 ? 0 : 30) : x >= 25 ? 20 : Infinity) : 0));
  naj = Math.min(naj, nar[0] + nar[1] + d[0] + d[1]);
}
assert.equal(r.kombinacijaDostava.ukupno, naj);

// Pregled narudžbe: dvije zasebne narudžbe (A cement, B ljepilo) s dostavom svake; stanje je samo izračun.
let pregled = run(app, "pregledNarudzbe(sveUJednomDucanu())");
assert.deepEqual(pregled.map((n) => [n.ime, n.materijal, n.dostava.cijena, n.stavke.map((x) => [x.stavka, x.pakiranja])]),
  [["A", 100, 30, [["Cement", 20]]], ["B", 90, 20, [["Ljepilo za pločice", 10]]]]);
run(app, "prikaziJednuTrgovinu()");
assert.match(app.__cvorovi["pregled-narudzbe"].children[0].children[2].textContent, /^Stanje: izračun – ništa nije poslano trgovcu\./);
assert.match(run(app, "tekstUpita(pregledNarudzbe(sveUJednomDucanu())[0])"), /Dostava na: 10000 Zagreb/);
// 7) Promjena načina: popis i količine ostaju, usporedbe se računaju iznova.
run(app, "postaviNacin(false)");
assert.equal(run(app, "stanje.dostava"), false);
assert.deepEqual(run(app, "stanje.popis.map((s) => s.kom)"), [20, 10]);
r = run(app, "prikaziJednuTrgovinu()");
assert.equal(r.dostava, undefined);
console.log("DELIVERY PASS: default without delivery, no postcode -> na upit and no winner, per-order fee, outside area and "
  + "below minimum -> na upit, free threshold, unknown never 0 or cheapest, combination with delivery = brute force, address "
  + "and mode change recompute and keep the list");

// Stvarna datoteka pravila: svako pravilo ima službeni URL, datum provjere i doslovni citat; nijedan iznos nije izmišljen.
const fs = require("fs");
const stvarna = JSON.parse(fs.readFileSync(require("path").join(__dirname, "../site/data/dostava.json"), "utf8"));
for (const [firma, p] of Object.entries(stvarna.pravila)) {
  assert.match(p.url, /^https:\/\//, firma);
  assert.match(p.provjereno, /^\d{4}-\d{2}-\d{2}$/, firma);
  assert.ok(p.citat && p.citat.length > 20, firma);
  assert.ok(p.vrsta === "na_upit" || (p.vrsta === "fiksno" && Number.isFinite(p.iznos)), firma);
}
app = scenarij(proizvodi, popis, stvarna.pravila);
run(app, `stanje.dostava = true; stanje.adresa = { mjesto: "Zagreb", postanski: "10000", ulica: "" };
  podaci.lanci = ["Gavroprom", "Veker", "Consortium (web)"]; podaci.firmeLanaca = ["Gavroprom", "Veker", "Consortium (web)"];`);
r = run(app, "prikaziJednuTrgovinu()");
assert.ok(r.potpune.every((x) => x.konacno === null && !x.najpovoljniji), "published weight-based terms stay 'na upit'");
assert.match(r.potpune.find((x) => x.ime === "Gavroprom").dostava.opis, /^Dostava na upit: .*gavroprom\.hr\/web\/placanje-i-dostava-webshop\/57\/, provjereno 23\.10\.2026\./);
assert.match(r.potpune.find((x) => x.ime === "Consortium (web)").dostava.opis, /nema objavljenu cijenu dostave/);
console.log("DELIVERY DATA PASS: every rule has official URL, date and quote; weight/destination-based terms stay 'na upit' with source");
