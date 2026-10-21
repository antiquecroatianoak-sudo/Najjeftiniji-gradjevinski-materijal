// „Sve u jednom dućanu“: potpune i nepotpune trgovine, izjednačeni pobjednici, zaokruživanje cijelih pakiranja,
// očuvanje tražene količine, jednakost sa zbrojem kartica otvorene trgovine, razlika prema kombinaciji, bez potpune.
// Sintetički cjenik (nisu stvarne cijene): node tests/sve-u-jednom.cjs
const assert = require("node:assert/strict");
const vm = require("vm");
const ucitaj = require("../scripts/aplikacija-vm.cjs");

function scenarij(proizvodi, popis) {
  const app = ucitaj({ datum: "2026-10-21", lanci: ["A", "B", "C"], vrsteIzvora: ["trgovina", "trgovina", "trgovina"], proizvodi });
  vm.runInContext(`
    const cvor = () => ({ children: [], hidden: false, textContent: "", className: "", set innerHTML(v) { this.children = []; },
      appendChild(c) { this.children.push(c); }, append(...c) { this.children.push(...c); }, setAttribute() {} });
    globalThis.__cvorovi = {};
    document.getElementById = (id) => __cvorovi[id] || (__cvorovi[id] = cvor());
    document.createElement = () => cvor();
    prikaziRezultate = () => {}; spremi = () => {};
    stanje.popis = ${JSON.stringify(popis)};
    // Zbroj kartica kad se trgovina otvori: isti izračun kao prikaziRezultate (odabrana ponuda × cijela pakiranja).
    globalThis.__kartice = (ime) => {
      stanje.jedna = ime; ponudeCache.clear();
      if (ime) stanje.odabir = odabirJedneTrgovine();
      let z = 0;
      for (const s of stanje.popis) {
        const lista = ponudeZaGrupu(s.naziv);
        if (!lista.length) continue;
        const p = lista[(stanje.odabir[s.naziv] || 0) % lista.length];
        z += p.cijena * brojPakiranja(s, p);
      }
      stanje.jedna = null; stanje.odabir = {}; ponudeCache.clear();
      return Math.round(z * 100) / 100;
    };
  `, app);
  return app;
}
const P = (naziv, iznos, jedinica, cijene) => [naziv, `${iznos} ${jedinica}`, iznos, jedinica, 0, cijene, "", null];
const popis = [{ naziv: "Cement", kom: 1, trazeno: { iznos: 60, jedinica: "kg" } }, { naziv: "Ljepilo za pločice", kom: 1 }];

// 1) A i B imaju sve, C nema cementa. 60 kg: A 3 × 25 kg, B 2 × 40 kg.
let app = scenarij([
  P("Cement CEM II 25 kg", 25, "kg", [0, 6]),
  P("Cement CEM II 40 kg", 40, "kg", [1, 9]),
  P("Ljepilo za pločice C2TE 25 kg", 25, "kg", [0, 10, 1, 9, 2, 8]),
], popis);
let r = vm.runInContext("prikaziJednuTrgovinu()", app);
assert.deepEqual(Array.from(r.potpune, (x) => [x.ime, x.ukupno, x.najpovoljniji]), [["B", 27, true], ["A", 28, false]]);
assert.equal(r.kombinacija, 26, "cement 18 (either) + adhesive 8 at C");
assert.deepEqual(Array.from(r.potpune, (x) => x.razlika), [1, 2], "difference to the cheapest multi-store combination");
assert.equal(r.nepotpune.length, 1);
assert.equal(r.nepotpune[0].ime, "C");
assert.equal(`${r.nepotpune[0].pokriveno}/${r.nepotpune[0].stavki}`, "1/2");
assert.deepEqual(Array.from(r.nepotpune[0].nedostaje), ["Cement"]);
assert(!r.nepotpune[0].najpovoljniji, "an incomplete store never wins, even with a lower partial sum");
for (const x of r.potpune) assert.equal(x.ukupno, app.__kartice(x.ime), `row ${x.ime} equals the sum of its opened cards`);
assert.equal(vm.runInContext(`brojPakiranja(stanje.popis[0], ponudeZaGrupu("Cement", new Set([0]))[0], true)`, app), 3, "60 kg → 3 × 25 kg");
assert.equal(vm.runInContext(`brojPakiranja(stanje.popis[0], ponudeZaGrupu("Cement", new Set([1]))[0], true)`, app), 2, "60 kg → 2 × 40 kg");
assert.equal(vm.runInContext("stanje.popis[0].trazeno.iznos", app), 60, "requested quantity is kept");
const redovi = app.__cvorovi["trgovine-usporedba"].children;
assert.equal(redovi.length, 2);
assert.match(redovi[0].children[0].className, /najpovoljniji/);
assert.equal(redovi[0].children[0].children[0].children[0].textContent, "★ Najpovoljniji lanac", "meaning not by colour alone");
assert(!/najpovoljniji/.test(redovi[1].children[0].className));
assert.equal(app.__cvorovi["nema-potpune"].hidden, true);
assert.equal(app.__cvorovi["nepotpune-naslov"].hidden, false);

// 2) Jednaki iznosi: oba najpovoljnija (na cent, bez greške zaokruživanja 0,1 + 0,2).
app = scenarij([
  P("Cement CEM II 25 kg", 25, "kg", [0, 0.1, 1, 0.2]),
  P("Ljepilo za pločice C2TE 25 kg", 25, "kg", [0, 0.2, 1, 0.1]),
], [{ naziv: "Cement", kom: 1 }, { naziv: "Ljepilo za pločice", kom: 1 }]);
r = vm.runInContext("prikaziJednuTrgovinu()", app);
assert.deepEqual(Array.from(r.potpune, (x) => x.najpovoljniji), [true, true], "ties: all cheapest complete stores marked");

// 3) Nijedna trgovina nema sve: bez pobjednika, jasna poruka.
app = scenarij([
  P("Cement CEM II 25 kg", 25, "kg", [0, 6]),
  P("Ljepilo za pločice C2TE 25 kg", 25, "kg", [1, 9]),
], popis);
r = vm.runInContext("prikaziJednuTrgovinu()", app);
assert.equal(r.potpune.length, 0);
assert.equal(app.__cvorovi["nema-potpune"].hidden, false, "states clearly that no store has everything");
assert.equal(r.nepotpune.length, 3, "including the store with 0/2");
assert(r.nepotpune.every((x) => !x.najpovoljniji));
assert.equal(r.kombinacija, 18 + 9, "the multi-store combination still exists across two stores");
// Cijela pakiranja odlučuju, ne jedinična cijena (isti nalaz kao košarica #11): 50 kg cementa.
// A: 40 kg za 9,00 € (0,225 €/kg) → 2 vreće = 18,00 €; A ima i 25 kg za 6,00 € (0,24 €/kg) → 2 vreće = 12,00 €.
app = scenarij([P("Cement CEM II 40 kg", 40, "kg", [0, 9]), P("Cement CEM II 25 kg", 25, "kg", [0, 6, 1, 6.5])],
  [{ naziv: "Cement", kom: 1, trazeno: { iznos: 50, jedinica: "kg" } }]);
r = vm.runInContext("prikaziJednuTrgovinu()", app);
assert.deepEqual(Array.from(r.potpune, (x) => [x.ime, x.ukupno]), [["A", 12], ["B", 13]], "A: 2 × 25 kg, not 2 × 40 kg");
assert.equal(r.kombinacija, 12);
assert.equal(r.potpune[0].ukupno, app.__kartice("A"), "opened A cards equal its row");
assert.equal(vm.runInContext("stanje.popis[0].trazeno.iznos", app), 50);
// Trgovina bez ijedne stavke (0/Y) prikazana je odvojeno, bez iznosa.
assert.equal(`${r.nepotpune[0].ime} ${r.nepotpune[0].pokriveno}/${r.nepotpune[0].stavki}`, "C 0/1");
assert.equal(app.__cvorovi["trgovine-nepotpune"].children[0].children[0].children[1].textContent, "—");
console.log("ONE-STORE PASS: complete vs incomplete, X/Y and missing items, ties, cents, whole packs, kept quantity, "
  + "row = opened cards, difference to combination, no complete store, whole-pack cost over unit price, 0/Y stores");
