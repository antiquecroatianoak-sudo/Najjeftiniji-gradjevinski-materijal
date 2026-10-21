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

const izvjestaj = { cjenik: podaci.datum, proizvoda: podaci.proizvodi.length, razvrstano: g.ukupno - g.nerazvrstano,
  nerazvrstano: g.nerazvrstano, poIzvoru, vrste, gubici };
fs.writeFileSync(path.join(path.dirname(ulaz), "revizija.json"), JSON.stringify(izvjestaj, null, 1));
console.log(`Revizija: ${izvjestaj.proizvoda} proizvoda, razvrstano ${izvjestaj.razvrstano}, nerazvrstano ${izvjestaj.nerazvrstano} (ostaju u pretrazi i označeni za provjeru)`);
for (const s of poIzvoru) console.log(`  ${s.naziv}: ${s.ponuda} ponuda, razvrstano ${s.razvrstano}, nerazvrstano ${s.nerazvrstano}` + (s.primjeri.length ? ` | npr. ${s.primjeri.slice(0, 3).join(" ; ")}` : ""));
for (const v of vrste) console.log(`  vrsta ${v.id}: ${v.proizvoda} proizvoda, ${v.mogucih} mogućih za provjeru`);
console.log(gubici.length ? `GUBICI u pretrazi: ${JSON.stringify(gubici)}` : "Pretraga: nijedan razvrstan proizvod ne nestaje (naziv, VELIKA slova, bez dijakritike)");
process.exitCode = gubici.length ? 1 : 0;
