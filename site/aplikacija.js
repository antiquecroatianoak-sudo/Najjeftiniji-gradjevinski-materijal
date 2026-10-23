"use strict";

// Osnovne jedinice za usporedbu; m2 i m3 prikazuju se kao m² i m³.
const JEDINICE = ["kg", "l", "kom", "m", "m2", "m3"];
const oznakaJedinice = (j) => j === "m2" ? "m²" : j === "m3" ? "m³" : j;

// ---------- Stanje aplikacije (sprema se u mobitel) ----------
const SPREMISTE = "gradjevina-v1";
let stanje = {
  popis: [],          // [{ naziv, kom, kupljeno, trazeno? }]; trazeno = { iznos, jedinica } u osnovnoj jedinici
  zakljucano: false,
  odabir: {},         // grupa -> redni broj ponude
  odabirSvi: {},      // odabir iz pregleda svih trgovina; referentna količina za usporedbu
  nacin: "jedinica",  // Poredak uvijek određuje jedinična cijena.
  iskljuceni: [],     // nazivi lanaca koji korisniku ne odgovaraju
  jedna: null,        // naziv lanca ako se kupuje sve u jednoj trgovini
  dostava: false,     // false = Bez dostave (samo materijal), true = S dostavom na adresu gradilišta
  adresa: { mjesto: "", postanski: "", ulica: "" }, // samo u ovom pregledniku; ne šalje se nikamo
};
try { Object.assign(stanje, JSON.parse(localStorage.getItem(SPREMISTE)) || {}); } catch (e) {}
// Starija verzija je spremala popis kao obične tekstove.
stanje.popis = (Array.isArray(stanje.popis) ? stanje.popis : [])
  .map((s) => typeof s === "string" ? { naziv: s, kom: 1, kupljeno: false } : s)
  .filter((s) => s && typeof s.naziv === "string" && s.naziv.trim())
  .map((s) => ({ naziv: s.naziv, kom: Math.min(99, Math.max(1, Math.floor(Number(s.kom) || 1))), kupljeno: !!s.kupljeno,
    ...(valjanoTrazeno(s.trazeno) ? { trazeno: { iznos: s.trazeno.iznos, jedinica: s.trazeno.jedinica } } : {}) }));
stanje.iskljuceni = Array.isArray(stanje.iskljuceni) ? stanje.iskljuceni : [];
stanje.odabir = stanje.odabir && typeof stanje.odabir === "object" ? stanje.odabir : {};
stanje.nacin = "jedinica";
// Svako otvaranje započinje usporedbom svih lanaca.
stanje.iskljuceni = [];
stanje.jedna = null;
stanje.odabir = {};
stanje.odabirSvi = {};
stanje.dostava = stanje.dostava === true;
stanje.adresa = { mjesto: String(stanje.adresa?.mjesto || "").slice(0, 80), postanski: String(stanje.adresa?.postanski || "").slice(0, 5),
  ulica: String(stanje.adresa?.ulica || "").slice(0, 120) };
function valjanoTrazeno(t) {
  return !!t && JEDINICE.includes(t.jedinica) && Number.isFinite(t.iznos) && t.iznos > 0 && t.iznos <= 100000;
}
function spremi() {
  try { localStorage.setItem(SPREMISTE, JSON.stringify(stanje)); } catch (e) {}
}

// ---------- Podaci o cijenama ----------
// { datum, lanci: [...], vrsteIzvora: [...], proizvodi: [[naziv, količina, iznos, jedinica, riječi marke,
//   [lanac, cijena, ...], specifikacija, podaci o ponudi], ...] }
// Specifikacija (npr. "debljina 10 cm · EPS") razdvaja proizvode koji se ne smiju uspoređivati po istoj jedinici.
// Podaci o ponudi: { izvor, url, provjereno, stanje, napomena } za oglase i ponude s posebnim uvjetima.
let podaci = null;
let klasifikacija = null;
let rijeci = [];       // za svaki proizvod: normalizirane riječi naziva
const pogociCache = new Map();
const ponudeCache = new Map();

const $ = (id) => document.getElementById(id);
const euro = (x) => x.toFixed(2).replace(".", ",") + " €";

// "Mlijeko Trajno" -> "mlijeko trajno", "šećer" -> "secer"
function normaliziraj(tekst) {
  return tekst.toLowerCase().replace(/đ/g, "d").normalize("NFD")
    .replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, " ").trim();
}

// Korijen riječi da "mlijeko" nađe i "mlijeka", "jaja" i "jaje" itd.
function korijen(rijec) {
  return rijec.length >= 4 ? rijec.replace(/[aeiou]+$/, "") : rijec;
}

// Padežni i množinski nastavci. "sir" tako nađe "sira", ali ne i "sirup".
const NASTAVCI = new Set(["", "a", "e", "i", "o", "u", "om", "em", "im", "ima", "ama", "ih", "oj", "og",
  "ov", "ova", "ove", "ovi", "ovo", "ev", "eva", "eve", "evi", "ja", "je", "ji", "ju", "jom",
  "ka", "ke", "ki", "ko", "ku", "ica", "ice", "ici"]);
// Riječ iza ovih ne opisuje sam proizvod: "čokolada s mlijekom", "jogurt od jagode".
const PRIJEDLOZI = new Set(["s", "sa", "od", "za", "u", "na", "bez", "iz", "po"]);

async function ucitajPodatke() {
  $("ponovi").hidden = true;
  $("status").textContent = "Učitavam cijene…";
  $("status").parentElement.classList.remove("greska", "spremno");
  try {
    const odgovor = await fetch("data/proizvodi.json", { cache: "no-cache" });
    if (!odgovor.ok) throw new Error(odgovor.status);
    const novi = await odgovor.json();
    if (!novi || !Array.isArray(novi.proizvodi) || !novi.proizvodi.length || !Array.isArray(novi.lanci)
        || !novi.lanci.length || !/^\d{4}-\d{2}-\d{2}$/.test(novi.datum)) throw new Error("Neispravan cjenik");
    podaci = novi;
    pogociCache.clear();
    ponudeCache.clear();
    if (podaci.verzija !== 2) {
      // Stari oblik: [naziv, količina, lanac, cijena]
      podaci.proizvodi = podaci.proizvodi.map(([n, k, l, c]) => [n, k, 0, "", 0, [l, c]]);
    }
    // Zaštita i za stare/offline cjenike: ne prikazuj ponude od jednog centa.
    podaci.proizvodi = podaci.proizvodi.map((p) => {
      const cijene = [];
      const tragovi = [];
      for (let k = 0; k < p[5].length; k += 2) {
        const c = p[5][k + 1];
        if (typeof c === "number" && Number.isFinite(c) && Math.round(c * 100) > 1) {
          cijene.push(p[5][k], c);
          tragovi.push(Array.isArray(p[8]) && Array.isArray(p[8][k / 2]) ? p[8][k / 2] : null);
        }
      }
      return [...p.slice(0, 5), cijene, typeof p[6] === "string" ? p[6] : "", p[7] && typeof p[7] === "object" ? p[7] : null, tragovi];
    }).filter((p) => p[5].length);
    if (!podaci.proizvodi.length) throw new Error("Nema valjanih cijena");
    rijeci = podaci.proizvodi.map((p) => normaliziraj(p[0]).split(" "));
    klasifikacija = null;
    if (typeof Skupine !== "undefined") {
      try {
        const indeksOdgovor = await fetch("data/skupine.json", { cache: "no-cache" });
        if (indeksOdgovor.ok) klasifikacija = Skupine.pripremi(podaci.proizvodi, await indeksOdgovor.json(), rijeci);
      } catch (e) { /* Cjenik ostaje dostupan i ako indeks nedostaje ili je zastario. */ }
    }
    await ucitajDostavu();
    const [g, m, d] = podaci.datum.split("-");
    $("status").textContent =
      `Cijene od ${d}.${m}.${g}. · ${podaci.proizvodi.length.toLocaleString("hr-HR")} ponuda · `
      + `${new Set(Array.isArray(podaci.firmeLanaca) ? podaci.firmeLanaca : podaci.lanci).size} firmi`;
    $("status").parentElement.classList.add("spremno");
  } catch (e) {
    podaci = null;
    klasifikacija = null;
    rijeci = [];
    $("ponovi").hidden = false;
    $("status").parentElement.classList.add("greska");
    $("status").textContent = "Cijene nisu dostupne. Tvoj popis ostaje spremljen.";
  }
  prikaziPostavke();
  prikazi();
}

// ---------- Pretraživanje ----------
// Indeksi proizvoda koji odgovaraju grupi (npr. "mlijeko").
function pogoci(grupa) {
  if (pogociCache.has(grupa)) return pogociCache.get(grupa);
  if (klasifikacija) {
    const prepoznati = klasifikacija.pogoci(grupa);
    if (prepoznati !== null) {
      // Uz razvrstane i moguće članove i nerazvrstani proizvodi sa svim riječima upita, da nijedan ne nestane
      // (revizija run 36: „List za pilu“ za upit „list pilu“). Oni su „vrsta za provjeru“ i ne rangiraju se.
      const vidjeno = new Set([...prepoznati, ...klasifikacija.moguciPogoci(grupa)]);
      const korijeniUpita = normaliziraj(grupa).split(" ").filter((w) => w && !PRIJEDLOZI.has(w)).map(korijen);
      const tekstom = korijeniUpita.length
        ? trazi(korijeniUpita, (w, k) => w.startsWith(k) && NASTAVCI.has(w.slice(k.length))).filter((i) => !klasifikacija.vrstaProizvoda(i))
        : [];
      const rezultat = [...vidjeno, ...tekstom.filter((i) => !vidjeno.has(i))];
      pogociCache.set(grupa, rezultat);
      return rezultat;
    }
  }
  const korijeni = normaliziraj(grupa).split(" ").filter(Boolean).map(korijen);
  let rezultat = [];
  if (korijeni.length) {
    rezultat = trazi(korijeni, (w, k) => w.startsWith(k) && NASTAVCI.has(w.slice(k.length)));
    if (!rezultat.length) rezultat = trazi(korijeni, (w, k) => w.startsWith(k));
  }
  pogociCache.set(grupa, rezultat);
  return rezultat;
}

function trazi(korijeni, odgovara) {
  const razine = [[], [], []];
  for (let i = 0; i < rijeci.length; i++) {
    const r = rijeci[i];
    if (!korijeni.every((k) => r.some((w) => odgovara(w, k)))) continue;
    const marka = podaci.proizvodi[i][4];
    const mjesto = r.findIndex((w) => odgovara(w, korijeni[0]));
    // 0: naziv počinje traženom riječi (ne računajući marku), npr. "Dukat Mlijeko…"
    // 1: riječ je negdje u nazivu, 2: riječ je iza prijedloga ("…s mlijekom")
    const razina = mjesto <= marka ? 0 : PRIJEDLOZI.has(r[mjesto - 1]) ? 2 : 1;
    razine[razina].push(i);
  }
  // Sve razine redom (početak naziva, sredina, iza prijedloga): nijedan pogodak ne nestaje zato što drugi
  // proizvodi počinju traženom riječi (revizija run 31: „R CW profil“ je nestajao uz „Profil …“).
  return razine.flat();
}

// ---------- Ponude ----------
function sviLanci() {
  if (!podaci) return new Set();
  const iskljuceni = new Set(stanje.iskljuceni);
  return new Set(podaci.lanci.map((_, i) => i).filter((i) => !iskljuceni.has(podaci.lanci[i])));
}

function dozvoljeniLanci() {
  const svi = sviLanci();
  const jedna = podaci ? podaci.lanci.indexOf(stanje.jedna) : -1;
  return jedna >= 0 && svi.has(jedna) ? new Set([jedna]) : svi;
}

// Trag cijene u službenom cjeniku: [redak, šifra, akcija, osnova količine, naziv akcije].
function ponuda(i, lanac, cijena) {
  const [, , iznos, jedinica, , cijene, spec = "", meta = null, tragovi = []] = podaci.proizvodi[i];
  let trag = null;
  for (let k = 0; k < cijene.length; k += 2) if (cijene[k] === lanac) { trag = (tragovi || [])[k / 2] || null; break; }
  return { i, lanac, cijena, jedinica, spec, meta, trag, poJedinici: iznos ? cijena / iznos : null,
    vrstaNejasna: !!klasifikacija && !klasifikacija.vrstaProizvoda(i) };
}

function imaJedinicnu(p) {
  return !p.vrstaNejasna && Number.isFinite(p.poJedinici) && p.poJedinici > 0 && JEDINICE.includes(p.jedinica);
}

// Ista jedinica i ista specifikacija; različite debljine ili razredi se ne uspoređuju.
const kljucJedinice = (p) => p.jedinica + "|" + (p.spec || "");
const opisJedinice = (p) => oznakaJedinice(p.jedinica) + (p.spec ? ` (${p.spec})` : "");

// Različite jedinice ne smiju sakriti cijelu skupinu niti se uspoređivati brojčano.
// Najzastupljenija jedinica ide prva; sve druge i nepoznate količine ostaju dostupne.
function jediniceGrupe(grupa) {
  const broj = new Map();
  for (const i of pogoci(grupa)) {
    const p = ponuda(i, 0, 1);
    if (imaJedinicnu(p)) broj.set(kljucJedinice(p), (broj.get(kljucJedinice(p)) || 0) + 1);
  }
  return [...broj.keys()].sort((a, b) => broj.get(b) - broj.get(a) || a.localeCompare(b));
}

function usporedba(jedinice) {
  const red = (p) => imaJedinicnu(p) ? jedinice.indexOf(kljucJedinice(p)) : jedinice.length;
  return (a, b) => red(a) - red(b)
    || (imaJedinicnu(a) && imaJedinicnu(b) && kljucJedinice(a) === kljucJedinice(b)
      ? a.poJedinici - b.poJedinici || a.cijena - b.cijena
      : podaci.proizvodi[a.i][0].localeCompare(podaci.proizvodi[b.i][0], "hr"));
}

// Sve ponude za jednu grupu, od najisplativije prema skupljoj.
// Svaki proizvod se pojavljuje samo jednom, u najjeftinijem dopuštenom lancu.
function ponudeZaGrupu(grupa, lanci = dozvoljeniLanci()) {
  const prednost = stanje.popis.find((s) => s.naziv === grupa)?.trazeno?.jedinica || "";
  const kljuc = grupa + "|" + prednost + "|" + [...lanci].join(",");
  if (ponudeCache.has(kljuc)) return ponudeCache.get(kljuc);
  const ponude = [];
  for (const i of pogoci(grupa)) {
    const cijene = podaci.proizvodi[i][5];
    let najjeftinija = null;
    for (let k = 0; k < cijene.length; k += 2) {
      if (lanci.has(cijene[k]) && (!najjeftinija || cijene[k + 1] < najjeftinija.cijena)) {
        najjeftinija = ponuda(i, cijene[k], cijene[k + 1]);
      }
    }
    if (najjeftinija) ponude.push(najjeftinija);
  }
  // Jedinica koju je korisnik izgovorio ("20 m2") ima prednost pred najčešćom jedinicom.
  const jedinice = jediniceGrupe(grupa);
  ponude.sort(usporedba([...jedinice.filter((k) => k.startsWith(prednost + "|") && prednost),
    ...jedinice.filter((k) => !prednost || !k.startsWith(prednost + "|"))]));
  ponudeCache.set(kljuc, ponude);
  return ponude;
}

// Za "sve u jednoj trgovini": najbolja ponuda za grupu u svakom lancu.
// Najbolja ponuda svake trgovine za stavku. S navedenom stavkom bira se najmanji stvarni iznos za istu traženu
// količinu (cijena × cijela pakiranja), ne najniža jedinična cijena (npr. 2 × 25 kg može biti jeftinije od 1 × 40 kg).
function najboljePoLancu(grupa, lanci, trazenaJedinica = null, stavka = null) {
  const sve = [];
  for (const i of pogoci(grupa)) {
    const cijene = podaci.proizvodi[i][5];
    for (let k = 0; k < cijene.length; k += 2) {
      if (lanci.has(cijene[k])) sve.push(ponuda(i, cijene[k], cijene[k + 1]));
    }
  }
  // Osnovna jedinica ne ovisi o odabranoj trgovini ni broju pakiranja.
  const jedinica = trazenaJedinica || jediniceGrupe(grupa)[0] || null;
  const usporedi = usporedba(jediniceGrupe(grupa));
  const najbolje = new Map();
  const trosak = (p) => (stavka ? centi(p.cijena * brojPakiranja(stavka, p, true)) : 0);
  for (const p of sve.filter((p) => imaJedinicnu(p) && kljucJedinice(p) === jedinica)) {
    const dosad = najbolje.get(p.lanac);
    if (!dosad || trosak(p) - trosak(dosad) < 0 || (trosak(p) === trosak(dosad) && usporedi(p, dosad) < 0)) najbolje.set(p.lanac, p);
  }
  return { najbolje, usporedi };
}

// Pregled jedne trgovine zadržava referentni odabir; promjena dopuštenih trgovina ga briše.
function promijeniPostavke(zadrziReferencu = false) {
  ponudeCache.clear();
  stanje.odabir = {};
  if (!zadrziReferencu) stanje.odabirSvi = {};
  else if (!stanje.jedna) stanje.odabir = { ...stanje.odabirSvi };
  else if (podaci) stanje.odabir = odabirJedneTrgovine();
  spremi();
  prikazi();
}

// ---------- Dodavanje stavki (glasom ili rukom) ----------
const BROJEVI = {
  jedan: 1, jedna: 1, jedno: 1, jednu: 1, dva: 2, dvije: 2, dvoje: 2, tri: 3, troje: 3,
  cetiri: 4, pet: 5, sest: 6, sedam: 7, osam: 8, devet: 9, deset: 10,
};
const RE_BROJ = "(\\d+|" + Object.keys(BROJEVI).join("|") + ")";
const RE_KOMADA = "(?:x|×|puta|komada|komad|kom|pakiranja|pakiranje|paketa|paket|boce|bocu|boca|vrecice|limenke|vreca|vrece|vreca|kanta|kante|kanti|rola|role|rolu|paleta|palete|ploca|ploce|kutija|kutije)";
// Izgovorena mjerna jedinica znači traženu količinu: "20 m2 laminata", "2,5 kubika betona".
const MJERE = [
  [/^(m2|m²|kvadrat|kvadrata|kvadratnih metara|kvadratna metra|kvadratni metar)$/, "m2", 1],
  [/^(m3|m³|kubik|kubika|kubnih metara|kubna metra|kubni metar)$/, "m3", 1],
  [/^(m|metar|metra|metara|dužnih metara|duznih metara)$/, "m", 1],
  [/^(cm|centimetara|centimetra)$/, "m", 0.01],
  [/^(t|tona|tone|tonu)$/, "kg", 1000],
  [/^(kg|kila|kilu|kile|kilograma?)$/, "kg", 1],
  [/^(g|gr|grama)$/, "kg", 0.001],
  [/^(l|lit|litra|litre|litru|litara)$/, "l", 1],
  [/^(ml|mililitara)$/, "l", 0.001],
];
const RE_JEDINICA_RIJEC = /^(m2|m²|m3|m³|m|cm|t|kg|g|gr|l|ml|kvadrat\w*|kubi\w*|metar|metra|metara|tona|tone|kil\w*|lit\w*|grama)$/;
// Preostale mjere iza broja komada: "2 kg ..." bez naziva ostaju broj pakiranja.
const RE_MJERA = /^(kg|kila|kilu|kile|kilograma?|l|lit|litra|litre|litru|litara)\s+(.+)$/;
const RE_SITNA_MJERA = /^(g|gr|grama|dag|deka|dkg|ml|dl|decilitra|cl)\s+(.+)$/;
// "20 m2 laminata" -> { naziv: "laminata", kom: 1, trazeno: { iznos: 20, jedinica: "m2" } }
function rastaviMjeru(izvorno) {
  const rijeci = izvorno.trim().replace(/^(\d+(?:[.,]\d+)?)(?=[a-zA-Z²³])/, "$1 ").split(/\s+/);
  if (rijeci.length < 3 || !/^\d+(?:[.,]\d+)?$/.test(rijeci[0])) return null;
  const broj = parseFloat(rijeci[0].replace(",", "."));
  const mala = rijeci.map((r) => r.toLowerCase());
  for (let n = Math.min(3, rijeci.length - 2); n >= 1 && broj > 0; n--) {
    const hit = MJERE.find(([re]) => re.test(mala.slice(1, 1 + n).join(" ")));
    if (hit) return { naziv: rijeci.slice(1 + n).join(" "), kom: 1,
      trazeno: { iznos: Number((broj * hit[2]).toFixed(6)), jedinica: hit[1] } };
  }
  return null;
}

// "2 mlijeka" -> { naziv: "mlijeka", kom: 2 }; "kruh" -> { naziv: "kruh", kom: null }
function rastavi(dio) {
  let tekst = dio.toLowerCase().replace(/č|ć/g, "c").replace(/š/g, "s");
  const izvorno = dio;
  let kom = null;
  const mjera = rastaviMjeru(izvorno);
  if (mjera) return mjera;
  let m = tekst.match(new RegExp(`^${RE_BROJ}\\s*${RE_KOMADA}?\\s+(.+)$`));
  let ostatak = izvorno;
  if (m) {
    kom = BROJEVI[m[1]] || parseInt(m[1], 10);
    ostatak = izvorno.slice(izvorno.length - m[2].length);
    tekst = m[2];
    const mjera = tekst.match(RE_MJERA);
    const sitna = tekst.match(RE_SITNA_MJERA);
    if (mjera) ostatak = ostatak.slice(ostatak.length - mjera[2].length);
    else if (sitna) { ostatak = ostatak.slice(ostatak.length - sitna[2].length); kom = 1; }
  } else if ((m = tekst.match(new RegExp(`^(.+?)\\s+(?:x\\s*(\\d+)|(\\d+)\\s*(?:x|komada|kom))$`)))) {
    kom = parseInt(m[2] || m[3], 10);
    ostatak = izvorno.slice(0, m[1].length);
  }
  if (kom !== null) kom = Math.min(Math.max(kom, 1), 99);
  return { naziv: ostatak.trim(), kom };
}

const kljucStavke = (naziv) => normaliziraj(naziv).split(" ").map(korijen).join(" ");

function dodajIzTeksta(tekst) {
  const dijelovi = tekst
    .split(/(?<!\d),|,(?!\d)|;|\.(?!\d)|\s+i\s+|\s+pa\s+|\s+te\s+|\s+onda\s+/i)
    .map((s) => s.trim().replace(/^(i|još|jos|pa)\s+/i, ""))
    .filter(Boolean);
  for (const d of dijelovi) {
    const { naziv: n, kom, trazeno } = rastavi(d);
    if (!normaliziraj(n)) continue;
    const naziv = n.charAt(0).toUpperCase() + n.slice(1).toLowerCase();
    const postojeca = stanje.popis.find((p) => kljucStavke(p.naziv) === kljucStavke(naziv));
    if (postojeca) {
      if (trazeno) { postojeca.trazeno = trazeno; postojeca.kom = 1; }
      else if (kom) { postojeca.kom = kom; delete postojeca.trazeno; }
    } else stanje.popis.push({ naziv, kom: kom || 1, kupljeno: false, ...(trazeno ? { trazeno } : {}) });
  }
  spremi();
  prikazi();
}

function ukloni(i) {
  stanje.popis.splice(i, 1);
  spremi();
  prikazi();
}

function promijeniKolicinu(i, za) {
  const s = stanje.popis[i];
  if (s.trazeno) s.trazeno.iznos = Math.min(Math.max(Math.round(s.trazeno.iznos + za), 1), 100000);
  else s.kom = Math.min(Math.max(s.kom + za, 1), 99);
  spremi();
  prikazi();
}

// ---------- Prepoznavanje govora ----------
const Prepoznavanje = window.SpeechRecognition || window.webkitSpeechRecognition;
let slusac = null;

// Granice artikala prepoznaj iz poznatih naziva, a višerječne nazive zadrži.
// Neprepoznati dijelovi ostaju u tekstu; korisnik ih može urediti na popisu.
function razdvojiGlasovniPopis(tekst) {
  const poznati = [
    ...(typeof Skupine !== "undefined" ? [...Skupine.definicije.map((d) => d.naziv), ...(Skupine.poznatiNazivi || [])] : []),
    "ljepilo za pločice", "fasadna boja", "unutarnja boja", "građevinsko ljepilo",
  ].map((s) => normaliziraj(s).split(" ").map(korijen)).sort((a, b) => b.length - a.length);
  return tekst.split(/[;!?]|(?<!\d)[,.]|[,.](?!\d)|\s+(?:i|pa|te|onda)\s+/i).flatMap((dio) => {
    const rijeci = dio.trim().split(/\s+/).filter(Boolean);
    const norm = rijeci.map((r) => normaliziraj(r));
    const granice = [0];
    for (let i = 0; i < rijeci.length; i++) {
      const hit = poznati.find((p) => p.every((k, j) => norm[i+j]
        && norm[i+j].startsWith(k) && NASTAVCI.has(norm[i+j].slice(k.length))));
      if (!hit || (i && PRIJEDLOZI.has(norm[i-1]))) continue;
      let pocetak = i;
      // Količina pripada sljedećem artiklu, npr. „kruh dva mlijeka”.
      if (i && (/^\d+$/.test(norm[i-1]) || BROJEVI[norm[i-1]])) pocetak--;
      // "20 m2 laminata", "2 vreće cementa": broj i jedinica ili pakiranje pripadaju artiklu.
      else if (i > 1 && (RE_JEDINICA_RIJEC.test(rijeci[i-1].toLowerCase()) || new RegExp(`^${RE_KOMADA}$`).test(norm[i-1]))
        && (/^\d+(?:[.,]\d+)?$/.test(rijeci[i-2]) || BROJEVI[norm[i-2]])) pocetak -= 2;
      else if (i && /^\d+(?:[.,]\d+)?(m2|m²|m3|m³|m|kg|l|t)$/i.test(rijeci[i-1])) pocetak--;
      if (pocetak > granice[granice.length - 1]) granice.push(pocetak);
      i += hit.length - 1;
    }
    return granice.map((p, j) => rijeci.slice(p, granice[j+1] ?? rijeci.length).join(" ")).filter(Boolean);
  });
}

// Jedan pritisak = jedan artikl, kao prije kontinuiranog nabrajanja.
// Rezultat se odmah dodaje i sprema. Završetak nikad ne pokreće novi mikrofon.
function alternativniUnos() { $("unos").focus(); }

function pokreniSlusanje() {
  const poruka = $("glasovni-nacrt");
  const javi = (tekst) => { poruka.hidden = !tekst; poruka.textContent = tekst; };
  if (!Prepoznavanje) {
    javi("Ovaj preglednik ne podržava glasovni unos. Proizvod možeš upisati u polje ispod.");
    alternativniUnos();
    return;
  }
  if (slusac) { try { slusac.stop(); } catch (e) { slusac.onend(); } return; }
  let novi;
  try { novi = new Prepoznavanje(); }
  catch (e) { javi("Glasovni unos nije dostupan. Pokušaj ponovno ili upiši proizvod."); return; }
  slusac = novi;
  novi.lang = "hr-HR";
  novi.continuous = false;
  novi.interimResults = false;
  novi.maxAlternatives = 1;
  let dodano = false;
  let greska = false;
  const vrijedi = () => slusac === novi;
  novi.onresult = (e) => {
    if (!vrijedi() || dodano) return;
    const tekst = e.results[0][0].transcript.trim();
    if (!tekst) return;
    dodano = true;
    dodajIzTeksta(tekst);
    javi("Dodano: " + tekst + ". Za sljedeći artikl ponovno dodirni mikrofon.");
  };
  novi.onerror = (e) => {
    if (!vrijedi()) return;
    greska = true;
    const poruke = {
      "not-allowed": "Dopusti pristup mikrofonu u postavkama preglednika.",
      "audio-capture": "Mikrofon nije dostupan. Provjeri koristi li ga druga aplikacija.",
      "network": "Usluga prepoznavanja govora trenutačno nije dostupna preko mreže.",
      "no-speech": "Nije prepoznat govor. Ponovno dodirni mikrofon i reci jedan artikl.",
      "service-not-allowed": "Preglednik ne dopušta prepoznavanje govora.",
    };
    javi(poruke[e.error] || "Glasovni unos je prekinut. Pokušaj ponovno ili upiši proizvod.");
  };
  novi.onend = () => {
    if (!vrijedi()) return;
    slusac = null;
    $("mikrofon").classList.remove("slusa");
    $("mikrofon").setAttribute("aria-pressed", "false");
    $("mikrofon-tekst").textContent = "Reci jedan artikl";
    if (!dodano && !greska) javi("Nije prepoznat artikl. Ponovno dodirni mikrofon i pokušaj.");
  };
  javi("Reci jedan artikl, primjerice mlijeko. Nakon upisa ponovno dodirni mikrofon za sljedeći.");
  $("mikrofon").classList.add("slusa");
  $("mikrofon").setAttribute("aria-pressed", "true");
  $("mikrofon-tekst").textContent = "Slušam… (dodirni za kraj)";
  try { novi.start(); }
  catch (e) { greska = true; javi("Glasovni unos nije dostupan. Pokušaj ponovno ili upiši proizvod."); novi.onend(); }
}

// ---------- Prikaz ----------
function gumb(tekst, klasa, naKlik, oznaka) {
  const b = document.createElement("button");
  b.type = "button";
  b.className = klasa;
  b.textContent = tekst;
  if (oznaka) b.setAttribute("aria-label", oznaka);
  b.onclick = naKlik;
  return b;
}

function prikazi() {
  $("lanci-info").textContent = podaci ? `${sviLanci().size} od ${podaci.lanci.length} trgovina odabrano` : "Trgovine će se prikazati nakon učitavanja cijena.";
  prikaziPopis();
}

function prikaziPopis() {
  $("prazno").hidden = stanje.popis.length > 0;
  const n = stanje.popis.length;
  $("broj-stavki").textContent = `${n} ${n % 10 === 1 && n % 100 !== 11 ? "stavka" : n % 10 >= 2 && n % 10 <= 4 && (n % 100 < 12 || n % 100 > 14) ? "stavke" : "stavki"}`;
  prikaziRezultate();
}

// Količina na popisu uvijek označava broj cijelih pakiranja.
// Broj komada unutar pakiranja koristi se samo za jediničnu cijenu.
// Broj pakiranja prikazane ponude. U pregledu jedne trgovine to su cijela pakiranja za barem
// referentnu količinu iz pregleda svih trgovina, kako bi iznos odgovarao usporedbi trgovina.
// Tražena količina u osnovnoj jedinici ("20 m2 laminata") određuje broj pakiranja svake ponude.
function brojPakiranja(stavka, p, jednaTrgovina = !!stanje.jedna) {
  if (!imaJedinicnu(p)) return stavka.kom;
  if (stavka.trazeno) {
    return stavka.trazeno.jedinica === p.jedinica
      ? Math.ceil(stavka.trazeno.iznos / podaci.proizvodi[p.i][2] - 1e-9) : stavka.kom;
  }
  if (!jednaTrgovina) return stavka.kom;
  const ref = referentnaPonuda(stavka.naziv);
  if (!ref || !imaJedinicnu(ref) || kljucJedinice(ref) !== kljucJedinice(p)) return stavka.kom;
  return Math.ceil(podaci.proizvodi[ref.i][2] * stavka.kom / podaci.proizvodi[p.i][2] - 1e-9);
}

// Referentna količina: tražena količina ako je jedinica ista, inače broj pakiranja × sadržaj.
function referentnaKolicina(stavka, odabrana) {
  if (!odabrana || !imaJedinicnu(odabrana)) return 0;
  if (stavka.trazeno) return stavka.trazeno.jedinica === odabrana.jedinica ? stavka.trazeno.iznos : 0;
  return podaci.proizvodi[odabrana.i][2] * stavka.kom;
}

// Referentni artikl uvijek dolazi iz pregleda svih dopuštenih trgovina, pa odabir
// jedne trgovine ne mijenja traženu fizičku količinu.
function referentnaPonuda(grupa) {
  const sve = ponudeZaGrupu(grupa, sviLanci());
  const rb = stanje.jedna ? stanje.odabirSvi[grupa] : stanje.odabir[grupa];
  return sve[(rb || 0) % sve.length];
}

// Ponuda koju kartica prikazuje kad se otvori trgovina l: odabrana alternativa u otvorenoj
// trgovini, inače najpovoljnija po jedinici za referentnu količinu, inače prva ponuda te trgovine.
function ponudaZaLanac(stavka, l, najbolje) {
  const lista = ponudeZaGrupu(stavka.naziv, new Set([l]));
  if (!lista.length) return null;
  if (stanje.jedna === podaci.lanci[l] && stanje.odabir[stavka.naziv] !== undefined) {
    return lista[stanje.odabir[stavka.naziv] % lista.length];
  }
  const p = najbolje.get(l);
  return (p && lista.find((x) => x.i === p.i)) || lista[0];
}

// Zadani odabir kartica pri otvaranju jedne trgovine: iste ponude kao u njezinom retku usporedbe.
function odabirJedneTrgovine() {
  const l = podaci.lanci.indexOf(stanje.jedna);
  const { najboljePoStavci } = usporedbaKosarice();
  const odabir = {};
  for (const stavka of stanje.popis) {
    const lista = ponudeZaGrupu(stavka.naziv, new Set([l]));
    const p = najboljePoStavci.get(stavka.naziv)?.get(l);
    const rb = p ? lista.findIndex((x) => x.i === p.i) : -1;
    if (rb > 0) odabir[stavka.naziv] = rb;
  }
  return odabir;
}

// Sve trgovine uspoređuju istu fizičku količinu referentnih artikala.
// Količina = broj odabranih pakiranja × sadržaj pakiranja; ne zaokružuje se za usporedbu.
function usporedbaKosarice() {
  const lanci = sviLanci();
  // usporedno: jedinične cijene × referentna količina (samo usporedba, nije iznos na blagajni).
  // ukupno: zbroj kartica kad se ta trgovina otvori (cijela pakiranja); nema: bez usporedive ponude.
  const zbroj = new Map([...lanci].map((l) => [l, { usporedno: 0, ukupno: 0, nema: [], neusporedivo: [] }]));
  const najboljePoStavci = new Map();
  let najboljeMijesano = 0;
  let sveMijesanoIma = true;
  const jedinice = [];
  for (const stavka of stanje.popis) {
    const odabrana = referentnaPonuda(stavka.naziv);
    const kolicina = referentnaKolicina(stavka, odabrana);
    const { najbolje, usporedi } = kolicina > 0
      ? najboljePoLancu(stavka.naziv, lanci, kljucJedinice(odabrana), stavka)
      : { najbolje: new Map(), usporedi: () => 0 };
    najboljePoStavci.set(stavka.naziv, najbolje);
    const prva = [...najbolje.values()].sort(usporedi)[0];
    if (prva) {
      najboljeMijesano += prva.poJedinici * kolicina;
      jedinice.push(`${stavka.naziv}: ${Number(kolicina.toFixed(6)).toLocaleString("hr-HR")} ${opisJedinice(prva)}`);
    } else sveMijesanoIma = false;
    for (const [l, z] of zbroj) {
      const p = najbolje.get(l);
      if (p) z.usporedno += p.poJedinici * kolicina;
      else z.nema.push(stavka.naziv);
      // Isti izračun kao kartica u otvorenoj trgovini, uključujući ponude bez usporedive količine.
      const kartica = ponudaZaLanac(stavka, l, najbolje);
      if (kartica) {
        z.ukupno += kartica.cijena * brojPakiranja(stavka, kartica, true);
        if (!p || kartica.i !== p.i) z.neusporedivo.push(stavka.naziv);
      }
    }
  }
  return { zbroj, najboljeMijesano, sveMijesanoIma, jedinice, najboljePoStavci };
}

// Datum cjenika trgovca (stariji cjenici nemaju zaseban datum, pa vrijedi datum cijelog cjenika).
function datumCijene(lanac) {
  // Prazan datum: izvor bez datuma objave (oglas, cijena sa stranice proizvoda); vrijeme provjere je u detaljima ponude.
  if (podaci.datumiLanaca && podaci.datumiLanaca[lanac] === "") return "nije objavljen · vidi provjereno";
  const d = (podaci.datumiLanaca && podaci.datumiLanaca[lanac]) || podaci.datum;
  return /^\d{4}-\d{2}-\d{2}$/.test(d || "") ? d.split("-").reverse().join(".") + "." : "nepoznat";
}

const OSNOVA_KOLICINE = { p: "količinu potvrđuje cijena za jedinicu mjere", c: "količina iz cjenika",
  j: "količina iz cijene za jedinicu mjere", n: "količina samo u nazivu, nije potvrđena · bez poretka",
  x: "cijena za jedinicu mjere proturječi cijeni · bez poretka" };

// Gdje je cijena u službenom cjeniku: redak, šifra, akcija i poveznica na datoteku cjenika.
function opisTraga(p) {
  const t = p.trag;
  if (!t || t[0] === null || t[0] === undefined) return null;
  const div = document.createElement("div");
  div.className = "detalji trag-cijene";
  const tekst = document.createElement("span");
  tekst.textContent = ["Službeni cjenik", `redak ${t[0]}`, t[1] ? `šifra ${t[1]}` : "",
    t[2] ? `akcija${t[4] ? `: ${t[4]}` : ""}` : "", OSNOVA_KOLICINE[t[3]] || ""].filter(Boolean).join(" · ");
  div.appendChild(tekst);
  // Prodajna mjesta na koja se cjenik odnosi: isti cjenik firme ili (kad se cijene razlikuju) samo navedena mjesta.
  const mjesta = (podaci.mjestaLanaca || [])[p.lanac];
  if (Array.isArray(mjesta) && mjesta.length) {
    const m = document.createElement("span");
    m.textContent = (podaci.razlicitCjenikLanaca || [])[p.lanac]
      ? ` · cijena vrijedi za: ${mjesta.join(", ")} (druga prodajna mjesta firme imaju druge cijene)`
      : ` · isti cjenik u prodajnim mjestima: ${mjesta.join(", ")}`;
    div.appendChild(m);
  }
  const url = (podaci.urlLanaca || [])[p.lanac];
  if (/^https:\/\//.test(url || "")) {
    const a = document.createElement("a");
    a.href = url;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.textContent = "Otvori cjenik";
    div.appendChild(a);
  }
  return div;
}

// Izvor, stanje i datum provjere ponude (osobito oglasa). Poveznica vodi na izvornu ponudu.
function opisPonude(meta) {
  const div = document.createElement("div");
  div.className = "detalji";
  const tekst = document.createElement("span");
  const provjereno = /^\d{4}-\d{2}-\d{2}/.test(meta.provjereno || "")
    ? meta.provjereno.slice(0, 10).split("-").reverse().join(".") + "." : "";
  tekst.textContent = [meta.stanje === "rabljeno" ? "Rabljeno" : meta.stanje === "novo" ? "Novo" : "",
    meta.napomena || "", provjereno ? `provjereno ${provjereno}` : ""].filter(Boolean).join(" · ");
  div.appendChild(tekst);
  if (/^https:\/\//.test(meta.url || "")) {
    const a = document.createElement("a");
    a.href = meta.url;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.textContent = `Otvori na: ${meta.izvor || "izvoru"}`;
    div.appendChild(a);
  }
  return div;
}

function prikaziRezultate() {
  const ul = $("kartice");
  ul.innerHTML = "";
  let ukupno = 0;
  let preostalo = 0;
  let kupljeno = 0;
  let nedostaje = 0;
  let zaProvjeru = 0;
  const poLancu = {};
  const lanciOk = sviLanci().size > 0;

  $("samo-trgovina").hidden = !(podaci && dozvoljeniLanci().size === 1 && stanje.jedna);
  $("samo-trgovina-naziv").textContent = stanje.jedna || "";

  for (const [stavkaIndex, stavka] of stanje.popis.entries()) {
    const grupa = stavka.naziv;
    const li = document.createElement("li");
    li.className = "kartica";
    if (stavka.kupljeno) { li.classList.add("kupljeno"); kupljeno++; }
    const ponude = podaci && lanciOk ? ponudeZaGrupu(grupa) : [];

    const kvacica = gumb(stavka.kupljeno ? "✓" : "", "kvacica", (e) => {
      e.stopPropagation();
      stavka.kupljeno = !stavka.kupljeno;
      spremi();
      prikaziRezultate();
    }, stavka.kupljeno ? `Vrati ${grupa} među nenabavljeno` : `Označi ${grupa} kao nabavljeno`);
    const sadrzaj = document.createElement("div");
    sadrzaj.className = "sadrzaj";
    li.append(kvacica, sadrzaj);

    const naslov = document.createElement("div");
    naslov.className = "grupa";
    naslov.textContent = stavka.trazeno
      ? `${grupa} · ${stavka.trazeno.iznos.toLocaleString("hr-HR")} ${oznakaJedinice(stavka.trazeno.jedinica)}`
      : stavka.kom > 1 ? `${grupa} · ${stavka.kom} kom` : grupa;
    sadrzaj.appendChild(naslov);
    const kontrole = document.createElement("div");
    kontrole.className = "kontrole";
    const manje = gumb("−", "kolicina-gumb", () => promijeniKolicinu(stavkaIndex, -1), `Manje ${grupa}`);
    manje.disabled = stavka.trazeno ? stavka.trazeno.iznos <= 1 : stavka.kom <= 1;
    const broj = document.createElement("span");
    broj.className = "broj";
    broj.textContent = stavka.trazeno
      ? `${stavka.trazeno.iznos.toLocaleString("hr-HR")} ${oznakaJedinice(stavka.trazeno.jedinica)}` : `${stavka.kom}×`;
    kontrole.append(manje, broj,
      gumb("+", "kolicina-gumb", () => promijeniKolicinu(stavkaIndex, 1), `Više ${grupa}`),
      gumb("Ukloni", "ukloni", () => ukloni(stavkaIndex), `Ukloni ${grupa}`));
    sadrzaj.appendChild(kontrole);

    if (!ponude.length) {
      nedostaje++;
      li.classList.add("nema");
      const poruka = document.createElement("div");
      poruka.className = "naziv";
      poruka.textContent = !podaci ? "Cijene još nisu učitane."
        : !lanciOk ? "Odaberi barem jednu trgovinu iznad popisa."
        : stanje.jedna ? `Nema u trgovini ${stanje.jedna}.`
        : "Nema pronađenih ponuda u odabranim trgovinama.";
      sadrzaj.appendChild(poruka);
      ul.appendChild(li);
      continue;
    }

    const rb = (stanje.odabir[grupa] || 0) % ponude.length;
    const p = ponude[rb];
    if (p.vrstaNejasna) zaProvjeru++;
    const [naziv, kolicina] = podaci.proizvodi[p.i];
    const lanac = podaci.lanci[p.lanac];
    const pakiranja = brojPakiranja(stavka, p);
    const cijena = p.cijena * pakiranja;
    ukupno += cijena;
    if (!stavka.kupljeno) preostalo += cijena;
    poLancu[lanac] = (poLancu[lanac] || 0) + 1;

    sadrzaj.insertAdjacentHTML("beforeend", `
      <div class="naziv"></div>
      <dl class="podaci-ponude">
        <div><dt>Potrebno</dt><dd class="potrebno"></dd></div>
        <div><dt>Pakiranje</dt><dd class="kolicina"></dd></div>
        <div><dt>Jedinična cijena</dt><dd class="jedinicna"></dd></div>
        <div class="spec-polje" hidden><dt>Specifikacija</dt><dd class="specifikacija"></dd></div>
        <div><dt>Trgovac</dt><dd class="trgovina"></dd></div>
        <div><dt>Cijena od</dt><dd class="datum-cijene"></dd></div>
      </dl>
      <div class="redak"><span class="ukupno-oznaka">Ukupno</span><span class="cijena"></span></div>
      <div class="detalji"><span class="mjesto"></span></div>`);
    sadrzaj.querySelector(".naziv").textContent = naziv;
    sadrzaj.querySelector(".trgovina").textContent = lanac;
    sadrzaj.querySelector(".cijena").textContent = euro(cijena);
    sadrzaj.querySelector(".potrebno").textContent = stavka.trazeno
      ? `${stavka.trazeno.iznos.toLocaleString("hr-HR")} ${oznakaJedinice(stavka.trazeno.jedinica)}` : `${stavka.kom} kom`;
    sadrzaj.querySelector(".kolicina").textContent =
      [kolicina, `${pakiranja} × ${euro(p.cijena)}`].filter(Boolean).join(" · ");
    sadrzaj.querySelector(".jedinicna").textContent = p.vrstaNejasna ? "Moguće podudaranje · vrsta za provjeru"
      : imaJedinicnu(p) ? `${euro(p.poJedinici)}/${oznakaJedinice(p.jedinica)}`
      : p.meta?.razlog ? `Nije uspoređeno: ${p.meta.razlog}`
      : p.trag && ["n", "x"].includes(p.trag[3]) ? OSNOVA_KOLICINE[p.trag[3]] : "Količina nije poznata · bez poretka";
    sadrzaj.querySelector(".spec-polje").hidden = !p.spec;
    sadrzaj.querySelector(".specifikacija").textContent = p.spec || "";
    sadrzaj.querySelector(".datum-cijene").textContent = datumCijene(p.lanac);
    if (p.meta) sadrzaj.appendChild(opisPonude(p.meta));
    const trag = opisTraga(p);
    if (trag) sadrzaj.appendChild(trag);
    const mjesto = sadrzaj.querySelector(".mjesto");
    if (rb > 0) {
      mjesto.appendChild(gumb(`◀ ${rb + 1}. od ${ponude.length}`, "natrag", (e) => {
        e.stopPropagation();
        promijeni(grupa, -1);
      }));
    } else {
      mjesto.textContent = `${ponude.length} pronađenih proizvoda`;
    }
    const poredak = document.createElement("div");
    poredak.className = "detalji";
    if (imaJedinicnu(p)) {
      const iste = ponude.filter((x) => imaJedinicnu(x) && kljucJedinice(x) === kljucJedinice(p));
      const redni = iste.indexOf(p) + 1;
      poredak.textContent = `${redni === 1 ? "Najpovoljnije" : `${redni}. po cijeni`} po ${opisJedinice(p)} · ${iste.length} ponuda s tom jedinicom`;
    } else {
      poredak.textContent = p.vrstaNejasna
        ? "Provjeri odgovara li proizvod tvojem popisu. Ne proglašavamo ga najpovoljnijim."
        : "Ponuda je dostupna; povoljnost se ne može usporediti bez količine.";
    }
    sadrzaj.appendChild(poredak);
    if (ponude.length > 1) {
      sadrzaj.appendChild(gumb("Sljedeći proizvod →", "sljedeci", (e) => {
        e.stopPropagation();
        promijeni(grupa, +1);
      }, `Sljedeći proizvod za ${grupa}`));
    }
    kvacica.setAttribute("aria-pressed", String(!!stavka.kupljeno));
    ul.appendChild(li);
  }

  $("napredak").textContent = stanje.popis.length ? `Nabavljeno: ${kupljeno} od ${stanje.popis.length}` : "";
  $("ukupno").textContent = euro(ukupno);
  $("ukupno-oznaka").textContent = nedostaje ? "Iznos pronađenih proizvoda" : zaProvjeru ? "Iznos prikazanih ponuda" : "Za plaćanje · odabrana pakiranja";
  $("nedostaje").hidden = nedostaje === 0 && zaProvjeru === 0;
  $("nedostaje").textContent = [
    nedostaje ? `Za ${nedostaje} od ${stanje.popis.length} stavki nema cijene. Iznos ne obuhvaća cijeli popis.` : "",
    zaProvjeru ? `Za ${zaProvjeru} stavki provjeri vrstu prikazanog proizvoda prije kupnje.` : "",
  ].filter(Boolean).join(" ");
  $("preostalo").hidden = kupljeno === 0 || kupljeno === stanje.popis.length;
  $("preostalo-iznos").textContent = euro(preostalo);
  $("po-trgovinama").textContent = Object.entries(poLancu)
    .sort((a, b) => b[1] - a[1])
    .map(([l, n]) => `${l}: ${n}`)
    .join(" · ");
  prikaziNacin();
  prikaziJednuTrgovinu();
}

// Izbor Bez dostave / S dostavom i adresa gradilišta (adresa je obvezna samo uz dostavu).
function prikaziNacin() {
  const b = $("bez-dostave"), sd = $("s-dostavom");
  if (!b || !sd) return;
  b.setAttribute("aria-checked", String(!stanje.dostava));
  sd.setAttribute("aria-checked", String(stanje.dostava));
  b.classList[stanje.dostava ? "remove" : "add"]("odabran");
  sd.classList[stanje.dostava ? "add" : "remove"]("odabran");
  $("adresa-dostave").hidden = !stanje.dostava;
  $("napomena-dostava").textContent = stanje.dostava
    ? "Iznos je materijal; dostava po trgovcu je u usporedbi ispod (za cijelu narudžbu, ne po artiklu)."
    : "Bez dostave: iznos je samo materijal.";
}

function postaviNacin(sDostavom) {
  if (stanje.dostava === sDostavom) return;
  stanje.dostava = sDostavom;
  spremi();
  prikazi(); // popis i količine ostaju; sve usporedbe se ponovno računaju
}

// Sve u jednom dućanu: ukupan iznos cijelog popisa u svakoj trgovini (cijela pakiranja, iste tražene količine,
// iste jedinice/specifikacije kao kartice te trgovine) i najpovoljnija kombinacija više trgovina.
// Pobijediti može samo trgovina s usporedivom ponudom za svaku stavku; nepotpune se prikazuju zasebno.
const centi = (x) => Math.round(x * 100);

function sveUJednomDucanu() {
  const { zbroj, najboljePoStavci, jedinice } = usporedbaKosarice();
  const stavki = stanje.popis.length;
  let kombinacija = 0;
  let kombinacijaNedostaje = 0;
  for (const stavka of stanje.popis) {
    // Po stavci najniži stvarni iznos cijelih pakiranja među trgovinama koje imaju usporedivu ponudu.
    const iznosi = [...(najboljePoStavci.get(stavka.naziv) || new Map()).values()]
      .map((p) => p.cijena * brojPakiranja(stavka, p, true));
    if (iznosi.length) kombinacija += Math.min(...iznosi);
    else kombinacijaNedostaje++;
  }
  const potpune = [];
  const nepotpune = [];
  for (const [l, z] of zbroj) {
    const red = { lanac: l, ime: podaci.lanci[l], ukupno: z.ukupno, pokriveno: stavki - z.nema.length, stavki,
      nedostaje: z.nema, rucniOdabir: z.neusporedivo.filter((n) => !z.nema.includes(n)) };
    if (!z.nema.length) potpune.push(red);
    else nepotpune.push(red); // i trgovine bez ijedne stavke (0/Y): korisnik vidi sve odabrane trgovine
  }
  if (stanje.dostava) {
    // S dostavom: konačni iznos = materijal + dostava firme za cijelu narudžbu; nepoznata dostava nema konačni iznos.
    for (const r of [...potpune, ...nepotpune]) {
      r.dostava = dostavaFirme(firmaLanca(r.lanac), r.ukupno);
      r.materijal = r.ukupno;
      r.konacno = r.dostava.stanje === "poznata" ? (centi(r.ukupno) + centi(r.dostava.cijena)) / 100 : null;
    }
    potpune.sort((a, b) => (a.konacno === null) - (b.konacno === null)
      || centi(a.konacno ?? a.ukupno) - centi(b.konacno ?? b.ukupno) || a.ime.localeCompare(b.ime, "hr"));
    const najmanjeK = potpune.find((r) => r.konacno !== null);
    // Troškovi stavki po trgovcu (centi) za optimum s dostavom.
    const troskovi = stanje.popis.map((stavka) => new Map([...(najboljePoStavci.get(stavka.naziv) || new Map())]
      .map(([l, p]) => [l, centi(p.cijena * brojPakiranja(stavka, p, true))])));
    const kombD = (troskovi.every((t) => t.size) ? kombinacijaSDostavom(troskovi) : null);
    for (const r of potpune) {
      r.najpovoljniji = !!najmanjeK && r.konacno !== null && centi(r.konacno) === centi(najmanjeK.konacno);
      r.razlika = kombD && r.konacno !== null ? (centi(r.konacno) - centi(kombD.ukupno)) / 100 : null;
    }
    return { potpune, nepotpune, stavki, jedinice, kombinacija: kombinacijaNedostaje ? null : kombinacija, kombinacijaNedostaje,
      dostava: true, kombinacijaDostava: kombD, jednaDostava: najmanjeK || null };
  }
  potpune.sort((a, b) => centi(a.ukupno) - centi(b.ukupno) || a.ime.localeCompare(b.ime, "hr"));
  nepotpune.sort((a, b) => b.pokriveno - a.pokriveno || a.ukupno - b.ukupno || a.ime.localeCompare(b.ime, "hr"));
  const najmanje = potpune.length ? centi(potpune[0].ukupno) : null;
  for (const r of potpune) {
    r.najpovoljniji = centi(r.ukupno) === najmanje; // svi izjednačeni najpovoljniji
    r.razlika = kombinacijaNedostaje ? null : (centi(r.ukupno) - centi(kombinacija)) / 100;
  }
  return { potpune, nepotpune, stavki, jedinice, kombinacija: kombinacijaNedostaje ? null : kombinacija, kombinacijaNedostaje };
}

// ---------- Dostava ----------
// Pravila dostave po firmi samo iz službenih uvjeta firme (data/dostava.json: URL, datum provjere, citat). Dostava se
// računa za cijelu narudžbu kod firme, nikad po artiklu. Bez primjenjivog pravila: "Dostava na upit" (nikad 0 €) i
// takav iznos ne može biti najpovoljniji konačni trošak.
let dostava = null;
async function ucitajDostavu() {
  try {
    const o = await fetch("data/dostava.json", { cache: "no-cache" });
    dostava = o.ok ? await o.json() : null;
  } catch (e) { dostava = null; }
}
const valjanPostanski = (p) => /^\d{5}$/.test(p || "");
function firmaLanca(l) {
  return String((Array.isArray(podaci.firmeLanaca) && podaci.firmeLanaca[l]) || podaci.lanci[l]).replace(/ \((web|oglasi)\)$/, "");
}
const izvorDostave = (p) => (p && p.url ? ` (uvjeti: ${p.url.replace(/^https:\/\/(www\.)?/, "")}${p.provjereno ? `, provjereno ${p.provjereno.split("-").reverse().join(".")}.` : ""})` : "");
// { stanje: "poznata" | "na-upit", cijena (€ ili null), opis, izvor: pravilo s URL-om i datumom }
function dostavaFirme(firma, iznos) {
  const p = dostava && dostava.pravila ? dostava.pravila[firma] : null;
  const naUpit = (opis, izvor = null) => ({ stanje: "na-upit", cijena: null, opis, izvor });
  if (!p) return naUpit("Dostava na upit: firma u našim podacima nema objavljenu cijenu dostave.");
  if (p.vrsta !== "fiksno") return naUpit(`Dostava na upit${p.napomena ? `: ${p.napomena}` : ""}${izvorDostave(p)}.`, p);
  if (!valjanPostanski(stanje.adresa.postanski)) return naUpit("Za izračun dostave upiši poštanski broj gradilišta.", p);
  const podrucje = p.podrucje && Array.isArray(p.podrucje.postanski) ? p.podrucje.postanski : null;
  if (podrucje && !podrucje.some((x) => stanje.adresa.postanski.startsWith(x))) {
    return naUpit("Adresa je izvan objavljenog područja dostave: dostava na upit.", p);
  }
  if (Number.isFinite(p.min_narudzba) && iznos < p.min_narudzba) {
    return naUpit(`Narudžba je ispod najmanjeg iznosa za dostavu (${euro(p.min_narudzba)}): dostava na upit.`, p);
  }
  const besplatno = Number.isFinite(p.besplatno_od) && iznos >= p.besplatno_od;
  return { stanje: "poznata", cijena: besplatno ? 0 : p.iznos, izvor: p,
    opis: (besplatno ? `Dostava besplatna (narudžba od ${euro(p.besplatno_od)})` : `Dostava ${euro(p.iznos)} po narudžbi`)
      + (p.ogranicenja ? ` · ${p.ogranicenja}` : "") };
}

// Točan optimum s dostavom: svi skupovi od najviše 3 trgovca s poznatom dostavom; svaka stavka kod najjeftinijeg
// trgovca iz skupa (cijela pakiranja), plus dostava svakog korištenog trgovca prema iznosu njegove narudžbe.
const NAJVISE_TRGOVACA = 3;
function kombinacijaSDostavom(troskovi) {
  const lanci = [...new Set(troskovi.flatMap((t) => [...t.keys()]))];
  const poznata = lanci.filter((l) => dostava?.pravila?.[firmaLanca(l)]?.vrsta === "fiksno");
  let naj = null;
  const skup = [];
  const probaj = () => {
    const narudzbe = new Map();
    const dodjela = [];
    let materijal = 0;
    for (const t of troskovi) {
      let m = null;
      for (const l of skup) if (t.has(l) && (m === null || t.get(l) < t.get(m))) m = l;
      if (m === null) return;
      dodjela.push(m);
      materijal += t.get(m);
      narudzbe.set(m, (narudzbe.get(m) || 0) + t.get(m));
    }
    let ukupno = materijal;
    const dostave = [];
    for (const [l, iznos] of narudzbe) {
      const d = dostavaFirme(firmaLanca(l), iznos / 100);
      if (d.stanje !== "poznata") return;
      ukupno += centi(d.cijena);
      dostave.push({ lanac: l, ime: podaci.lanci[l], materijal: iznos / 100, dostava: d });
    }
    if (!naj || ukupno < naj.ukupno || (ukupno === naj.ukupno && dostave.length < naj.dostave.length)) {
      naj = { ukupno, materijal, dostave, dodjela };
    }
  };
  const rek = (od) => {
    if (skup.length) probaj();
    if (skup.length === NAJVISE_TRGOVACA) return;
    for (let i = od; i < poznata.length; i++) { skup.push(poznata[i]); rek(i + 1); skup.pop(); }
  };
  rek(0);
  return naj && { ukupno: naj.ukupno / 100, materijal: naj.materijal / 100, dostave: naj.dostave, trgovaca: naj.dostave.length,
    dodjela: naj.dodjela };
}

function redTrgovine(r) {
  const li = document.createElement("li");
  const b = gumb("", "trgovina-red" + (r.najpovoljniji ? " najpovoljniji" : "") + (stanje.jedna === r.ime ? " odabrana" : "")
    + (r.nedostaje.length ? " nepotpun" : ""), () => {
    if (!stanje.jedna) stanje.odabirSvi = { ...stanje.odabir };
    stanje.jedna = stanje.jedna === r.ime ? null : r.ime;
    promijeniPostavke(true);
    window.scrollTo(0, 0);
  });
  const lijevo = document.createElement("span");
  lijevo.className = "lijevo";
  if (r.najpovoljniji) {
    const znacka = document.createElement("span");
    znacka.className = "znacka";
    znacka.textContent = "★ Najpovoljniji lanac";
    lijevo.appendChild(znacka);
  }
  const naziv = document.createElement("strong");
  naziv.textContent = r.ime;
  const opis = document.createElement("small");
  const opisDostave = r.dostava ? ` · ${r.dostava.opis}` : "";
  opis.textContent = (r.nedostaje.length
    ? `Pokriva ${r.pokriveno}/${r.stavki} · nedostaje: ${r.nedostaje.join(", ")}`
    : `Ima sve (${r.stavki}/${r.stavki})` + (r.razlika === null ? ""
      : r.razlika > 0 ? ` · ${euro(r.razlika)} više od najpovoljnije kombinacije` : " · jednako najpovoljnijoj kombinaciji")
      + (r.rucniOdabir.length ? ` · uključuje ručno odabrane ponude: ${r.rucniOdabir.join(", ")}` : "")) + opisDostave;
  lijevo.append(naziv, opis);
  const iznos = document.createElement("span");
  iznos.className = "iznos";
  iznos.textContent = !r.pokriveno ? "—" : r.dostava && r.konacno !== null ? euro(r.konacno)
    : r.dostava ? `${euro(r.ukupno)} + dostava na upit` : euro(r.ukupno);
  if (r.nedostaje.length && r.pokriveno) {
    const oznaka = document.createElement("small");
    oznaka.textContent = "djelomično, nije cijeli popis";
    iznos.appendChild(oznaka);
  }
  iznos.setAttribute("aria-label", r.nedostaje.length ? `Djelomični iznos ${euro(r.ukupno)}, nije cijeli popis`
    : r.dostava && r.konacno !== null ? `${euro(r.konacno)}: materijal ${euro(r.ukupno)} i dostava ${euro(r.dostava.cijena)}`
    : r.dostava ? `Materijal ${euro(r.ukupno)}, dostava na upit: konačni iznos nije poznat`
    : `${euro(r.ukupno)} za cijela pakiranja, isto kao zbroj kartica u toj trgovini`);
  b.append(lijevo, iznos);
  li.appendChild(b);
  return li;
}

// Dva rezultata s dostavom: Sve kod jednog trgovca i Najjeftinija kombinacija trgovaca (materijal + dostava svake narudžbe).
function opisSDostavom(rez) {
  const jedna = rez.jednaDostava;
  const k = rez.kombinacijaDostava;
  const dijelovi = [];
  dijelovi.push(jedna
    ? `Sve kod jednog trgovca: ${euro(jedna.konacno)} (${jedna.ime}: materijal ${euro(jedna.materijal)} + dostava ${euro(jedna.dostava.cijena)}; 1 dostava).`
    : "Sve kod jednog trgovca: nijedan potpuni trgovac nema poznatu dostavu na ovu adresu (dostava na upit).");
  dijelovi.push(k
    ? `Najjeftinija kombinacija (najviše ${NAJVISE_TRGOVACA} trgovca): ${euro(k.ukupno)} · ${k.trgovaca} ${k.trgovaca === 1 ? "trgovac" : "trgovca"}, `
      + `${k.trgovaca} ${k.trgovaca === 1 ? "dostava" : "zasebne dostave"} (materijal ${euro(k.materijal)}; `
      + k.dostave.map((d) => `${d.ime}: ${euro(d.dostava.cijena)}`).join(", ") + ")"
      + (jedna ? (centi(jedna.konacno) > centi(k.ukupno) ? ` · ušteda ${euro((centi(jedna.konacno) - centi(k.ukupno)) / 100)}` : " · jednako jednom trgovcu") : "") + "."
    : "Najjeftinija kombinacija s dostavom: nema potpune kombinacije s poznatom dostavom (dostava na upit).");
  if (rez.kombinacija !== null) dijelovi.push(`Samo materijal, bez dostave: ${euro(rez.kombinacija)}.`);
  return dijelovi.join(" ");
}

// ---------- Pregled narudžbe ----------
// Jedan pregled za cijeli popis: po trgovcu stavke, cijela pakiranja, iznos materijala i dostava. Stanja su odvojena:
// "Izračun" (ništa nije poslano), "Pripremljen upit" (tekst za korisnika, ne šalje se). "Poslan zahtjev" i "Potvrda
// trgovca" nisu podržani: nema dogovorenog kanala s trgovcima, pa se takva stanja nikad ne prikazuju.
function pregledNarudzbe(rez) {
  const { najboljePoStavci } = usporedbaKosarice();
  let dodjela;
  if (rez.dostava && rez.kombinacijaDostava) dodjela = rez.kombinacijaDostava.dodjela;
  else if (!rez.dostava && rez.kombinacija !== null) {
    dodjela = stanje.popis.map((stavka) => {
      let naj = null;
      for (const [l, p] of najboljePoStavci.get(stavka.naziv) || new Map()) {
        const c = centi(p.cijena * brojPakiranja(stavka, p, true));
        if (naj === null || c < naj[1]) naj = [l, c];
      }
      return naj && naj[0];
    });
  } else return null;
  const po = new Map();
  stanje.popis.forEach((stavka, j) => {
    const l = dodjela[j];
    const p = najboljePoStavci.get(stavka.naziv).get(l);
    const pakiranja = brojPakiranja(stavka, p, true);
    const r = po.get(l) || { lanac: l, ime: podaci.lanci[l], stavke: [], materijal: 0 };
    r.stavke.push({ stavka: stavka.naziv, proizvod: podaci.proizvodi[p.i][0], pakiranja, iznos: centi(p.cijena * pakiranja) / 100 });
    r.materijal = (centi(r.materijal) + centi(p.cijena * pakiranja)) / 100;
    po.set(l, r);
  });
  const narudzbe = [...po.values()];
  if (rez.dostava) for (const n of narudzbe) n.dostava = dostavaFirme(firmaLanca(n.lanac), n.materijal);
  return narudzbe;
}

function tekstUpita(n) {
  const a = stanje.adresa;
  return [`Upit za ponudu / dostavu – ${n.ime}`, "",
    ...n.stavke.map((x) => `- ${x.proizvod}: ${x.pakiranja} pak.`),
    "", `Iznos materijala prema objavljenom cjeniku: ${euro(n.materijal)}`,
    stanje.dostava ? `Dostava na: ${[a.ulica, [a.postanski, a.mjesto].filter(Boolean).join(" ")].filter(Boolean).join(", ") || "(adresa nije upisana)"}` : "Preuzimanje u trgovini",
    "Molim potvrdu raspoloživosti, cijene i uvjeta dostave."].join("\n");
}

function prikaziPregled(rez) {
  const ul = $("pregled-narudzbe");
  if (!ul) return;
  ul.innerHTML = "";
  const narudzbe = rez ? pregledNarudzbe(rez) : null;
  $("pregled-prazno").hidden = !!(narudzbe && narudzbe.length);
  if (!narudzbe) return;
  for (const n of narudzbe) {
    const li = document.createElement("li");
    li.className = "narudzba";
    const naslov = document.createElement("strong");
    naslov.textContent = `${n.ime} · materijal ${euro(n.materijal)}`
      + (n.dostava ? (n.dostava.stanje === "poznata" ? ` + dostava ${euro(n.dostava.cijena)}` : " + dostava na upit") : "");
    const stavke = document.createElement("small");
    stavke.textContent = n.stavke.map((x) => `${x.stavka}: ${x.pakiranja} × ${x.proizvod} (${euro(x.iznos)})`).join(" · ");
    const status = document.createElement("small");
    status.className = "stanje-narudzbe";
    status.textContent = "Stanje: izračun – ništa nije poslano trgovcu." + (n.dostava ? ` ${n.dostava.opis}` : "");
    const upit = gumb("Pripremi upit", "pripremi-upit", () => {
      const t = document.createElement("textarea");
      t.readOnly = true;
      t.rows = 6;
      t.value = tekstUpita(n);
      status.textContent = "Stanje: pripremljen upit – nije poslan. Kopiraj ga i pošalji trgovcu sam ako želiš.";
      li.appendChild(t);
      upit.disabled = true;
    }, `Pripremi tekst upita za ${n.ime}`);
    li.append(naslov, stavke, status, upit);
    ul.appendChild(li);
  }
}

function prikaziJednuTrgovinu() {
  const ul = $("trgovine-usporedba");
  const ulN = $("trgovine-nepotpune");
  ul.innerHTML = "";
  ulN.innerHTML = "";
  $("jedna-trgovina").hidden = !podaci || !stanje.popis.length;
  if (!podaci || !stanje.popis.length) return null;
  const rez = sveUJednomDucanu();
  $("kombinacija").textContent = rez.dostava ? opisSDostavom(rez)
    : rez.kombinacija !== null
    ? `Najpovoljnija kombinacija više trgovina: ${euro(rez.kombinacija)} (cijela pakiranja; svaka stavka u trgovini s najnižim iznosom).`
    : `Kombinacija više trgovina nije potpuna: za ${rez.kombinacijaNedostaje} od ${rez.stavki} stavki nema usporedive ponude.`;
  $("usporedne-kolicine").textContent = rez.jedinice.length ? `Iste količine u svakoj trgovini: ${rez.jedinice.join(" · ")}.` : "";
  $("nema-potpune").hidden = rez.potpune.length > 0;
  for (const r of rez.potpune) ul.appendChild(redTrgovine(r));
  $("nepotpune-naslov").hidden = !rez.nepotpune.length;
  for (const r of rez.nepotpune) ulN.appendChild(redTrgovine(r));
  prikaziPregled(rez);
  return rez;
}

function promijeni(grupa, smjer) {
  const n = ponudeZaGrupu(grupa).length;
  stanje.odabir[grupa] = ((stanje.odabir[grupa] || 0) + smjer + n) % n;
  if (!stanje.jedna) stanje.odabirSvi[grupa] = stanje.odabir[grupa];
  spremi();
  prikaziRezultate();
}

// ---------- Postavke ----------
// Izričit korisnički prioritet za hrvatsko tržište; nije rang po broju poslovnica.
// Trgovine prije oglasnika, zatim abecedno. Vrstu izvora određuje uvoz (data/proizvodi.json: vrsteIzvora).
function nazivLanca(ime) {
  const i = podaci ? podaci.lanci.indexOf(ime) : -1;
  return podaci?.vrsteIzvora?.[i] === "oglasnik" ? `${ime} (oglasi)` : ime;
}
function redoslijedLanaca(lanci) {
  const oglasnik = (ime) => Number(podaci?.vrsteIzvora?.[podaci.lanci.indexOf(ime)] === "oglasnik");
  // Sortira se kopija: izvorni indeksi cijena ostaju nepromijenjeni.
  return [...lanci].sort((a, b) => oglasnik(a) - oglasnik(b) || a.localeCompare(b, "hr"));
}
function prikaziPostavke() {
  for (const r of document.querySelectorAll('input[name="nacin"]')) r.checked = r.value === stanje.nacin;
  const div = $("lanci");
  div.innerHTML = "";
  if (!podaci) return;
  const iskljuceni = new Set(stanje.iskljuceni);
  redoslijedLanaca(podaci.lanci).forEach((ime) => {
    const label = document.createElement("label");
    const cb = document.createElement("input");
    cb.type = "checkbox";
    cb.checked = !iskljuceni.has(ime);
    cb.onchange = () => {
      stanje.iskljuceni = cb.checked
        ? stanje.iskljuceni.filter((x) => x !== ime)
        : [...stanje.iskljuceni, ime];
      if (!cb.checked && stanje.jedna === ime) stanje.jedna = null;
      promijeniPostavke();
    };
    label.append(cb, " " + nazivLanca(ime));
    div.appendChild(label);
  });
}

for (const r of document.querySelectorAll('input[name="nacin"]')) {
  r.onchange = () => { stanje.nacin = r.value; promijeniPostavke(); };
}
$("lanci-sve").onclick = () => { stanje.iskljuceni = []; prikaziPostavke(); promijeniPostavke(); };
$("lanci-nista").onclick = () => {
  stanje.iskljuceni = podaci ? [...podaci.lanci] : [];
  stanje.jedna = null;
  prikaziPostavke();
  promijeniPostavke();
};

// ---------- Gumbi ----------
$("ponovi").onclick = ucitajPodatke;
$("bez-dostave").onclick = () => postaviNacin(false);
$("s-dostavom").onclick = () => postaviNacin(true);
for (const [polje, kljuc] of [["adresa-postanski", "postanski"], ["adresa-mjesto", "mjesto"], ["adresa-ulica", "ulica"]]) {
  $(polje).value = stanje.adresa[kljuc];
  $(polje).addEventListener("input", () => {
    stanje.adresa[kljuc] = $(polje).value.trim();
    spremi();
    prikaziJednuTrgovinu(); // promjena adrese osvježava dostupnost i izračun dostave po trgovcu
  });
}
$("mikrofon").onclick = pokreniSlusanje;
$("rucni-unos").onsubmit = (e) => {
  e.preventDefault();
  const tekst = $("unos").value.trim();
  if (tekst) dodajIzTeksta(razdvojiGlasovniPopis(tekst).join(", "));
  $("unos").value = "";
};
$("samo-trgovina-makni").onclick = () => {
  stanje.jedna = null;
  promijeniPostavke(true);
};

prikaziPostavke();
prikazi();
ucitajPodatke();

if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(() => {});



