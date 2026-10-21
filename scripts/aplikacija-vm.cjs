// Učitava logiku aplikacije (site/aplikacija.js) bez preglednika, nad zadanim cjenikom: za reviziju i testove.
// Koriste se iste funkcije kao u aplikaciji (pogoci, ponudeZaGrupu, dozvoljeniLanci), ne kopija logike.
const fs = require("fs");
const path = require("path");
const vm = require("vm");
const Skupine = require("../site/skupine.js");

module.exports = function ucitajAplikaciju(podaci) {
  let izvor = fs.readFileSync(path.join(__dirname, "..", "site", "aplikacija.js"), "utf8");
  izvor = izvor.slice(0, izvor.lastIndexOf("\nfor (const r of document.querySelectorAll"));
  const ctx = vm.createContext({ Skupine, window: {}, localStorage: { getItem: () => null, setItem() {} },
    document: { addEventListener() {} }, console });
  vm.runInContext(izvor + `
    globalThis.__postavi = (p) => {
      podaci = p;
      rijeci = podaci.proizvodi.map((x) => normaliziraj(x[0]).split(" "));
      klasifikacija = Skupine.pripremi(podaci.proizvodi, null, rijeci);
      pogociCache.clear(); ponudeCache.clear();
    };
    globalThis.__filtar = (iskljuceni, jedna) => {
      stanje.iskljuceni = iskljuceni; stanje.jedna = jedna || null; pogociCache.clear(); ponudeCache.clear();
    };
    globalThis.__api = { pogoci, ponudeZaGrupu, dozvoljeniLanci, sviLanci, imaJedinicnu, stanje: () => stanje,
      klasifikacija: () => klasifikacija };
  `, ctx);
  ctx.__postavi(podaci);
  return ctx;
};
