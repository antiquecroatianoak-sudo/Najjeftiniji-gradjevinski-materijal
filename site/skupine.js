"use strict";

// Jedna pravila za cijeli cjenik. Marka, lanac i pakiranje ne određuju vrstu.
// Pravila su namjerno pregledna: nepoznat naziv ostaje neklasificiran i pretraživ.
(function (root) {
  const normaliziraj = (s) => String(s).toLowerCase().replace(/đ/g, "d").normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "").replace(/[^a-z0-9]+/g, " ").trim();
  const korijen = (s) => {
    const k = s.length >= 4 ? s.replace(/[aeiou]+$/, "") : s;
    return k.length < 3 ? s : k; // Kratke riječi (npr. „xps”) ostaju cijele.
  };
  const nastavci = new Set(["", "a", "ao", "e", "i", "o", "u", "om", "em", "im", "ima", "ama", "ih", "oj", "og", "ja", "je", "ji", "ju", "jom", "ovi", "ove", "ova", "evi", "eve"]);
  const odgovara = (w, k) => w.startsWith(k) && nastavci.has(w.slice(k.length));
  const prijedlozi = new Set(["s", "sa", "od", "za", "u", "na", "bez", "iz", "po"]);
  // id | naziv osnovne vrste | istovrijedni nazivi, a ne sastojci te vrste
  const zapis = `cement|Cement|cement
zbuka|Žbuka i mort|žbuka;malter;mort
ljepilo-plocice|Ljepilo za pločice|ljepilo za pločice;ljepilo za keramiku;fleksibilno ljepilo
ljepilo-stiropor|Ljepilo za izolaciju|ljepilo za stiropor;ljepilo za toplinsku izolaciju;ljepilo i masa za armiranje
ljepilo|Građevinsko ljepilo|ljepilo
fuga|Fuga|fuga;masa za fugiranje
gletna-masa|Gletna masa|gletna masa;glet masa;masa za gletanje
beton|Beton|beton;betonska mješavina;suhi beton
pijesak|Pijesak|pijesak
sljunak|Šljunak i tucanik|šljunak;tucanik;kamena sitnež
vapno|Vapno|vapno
gips|Gips|gips;gipsana masa
gipskarton|Gipskartonska ploča|gipskartonska ploča;gips ploča;gk ploča;rigips ploča;knauf ploča
opeka|Opeka i blokovi|opeka;cigla;blok;porobeton;ytong;siporex
crijep|Crijep|crijep
eps|EPS stiropor|stiropor;eps ploča;eps
xps|XPS ploče|xps;stirodur
mineralna-vuna|Mineralna vuna|mineralna vuna;kamena vuna;staklena vuna
hidroizolacija|Hidroizolacija|hidroizolacija;bitumenska traka;hidroizolacijska traka;hidroizolacijski premaz
folija|Građevinska folija|građevinska folija;pe folija;parna brana;folija
armatura|Armatura|armatura;armaturna mreža;rebrasta šipka;betonsko željezo
profil-suha-gradnja|Profili za suhu gradnju|cd profil;ud profil;cw profil;uw profil
osb|OSB ploče|osb;osb ploča
iverica|Iverica|iverica
sperploca|Šperploča|šperploča
letva|Letve|letva
greda|Grede|greda;gredica
daska|Daske|daska;blanjanac;fosna
laminat|Laminat|laminat
parket|Parket|parket
plocice|Keramičke pločice|keramičke pločice;pločice;granitogres
boja-zid|Boja za zidove|boja za zidove;unutarnja boja;disperzija;poludisperzija
fasadna-boja|Fasadna boja|fasadna boja;boja za fasadu
temeljni-premaz|Temeljni premaz|temeljni premaz;dubinska impregnacija
boja|Boje i lakovi|boja;lak;lazura
silikon|Silikon i kitovi|silikon;akrilni kit;kit
pjena|Montažna pjena|montažna pjena;pur pjena;pu pjena
fasadna-mreza|Fasadna mrežica|fasadna mreža;fasadna mrežica;staklena mrežica
vijak|Vijci|vijak;vijci
cavao|Čavli|čavao;čavli
tipla|Tiple|tipla;tiple
pvc-cijev|PVC cijevi|pvc cijev;kanalizacijska cijev
cijev|Cijevi|cijev
kabel|Kabeli|kabel;kabl
oluk|Oluci|oluk;žlijeb
mjesalica|Mješalice za beton|mješalica za beton;mješalica
busilica|Bušilice|bušilica;udarna bušilica;aku bušilica
brusilica|Brusilice|brusilica;kutna brusilica
kolica|Građevinska kolica|građevinska kolica;kolica;tačke
ljestve|Ljestve|ljestve;ljestvice
skela|Skele|skela
lopata|Lopate|lopata
zlica|Zidarske žlice i gleterice|zidarska žlica;mistrija;gleterica
rukavice|Radne rukavice|radne rukavice;rukavice`;

  const vrste = zapis.split("\n").map((s) => {
    const [id, naziv, aliases] = s.split("|");
    return { id, naziv, aliases: aliases.split(";").map((a) => normaliziraj(a).split(" ").map(korijen)) };
  });
  const definicije = new Map(vrste.map((v) => [v.id, v]));
  const indeks = new Map();
  for (const v of vrste) for (const alias of v.aliases) {
    const k = alias[0].slice(0, 3);
    if (!indeks.has(k)) indeks.set(k, []);
    indeks.get(k).push({ v, alias });
  }
  // Građevinski materijal nema okuse; specifikacije (debljina, razred) odvaja uvoz cjenika.
  const voce = new Set();
  const okusiVrste = new Set();
  const overrides = new Map([
    ["ljepilo", new Set(["ljepilo-plocice", "ljepilo-stiropor"])],
    ["boja", new Set(["boja-zid", "fasadna-boja", "temeljni-premaz"])],
    ["cijev", new Set(["pvc-cijev"])],
  ]);

  // Roditelj → djeca unutar ovog popisa vrsta (ista veza kao kod prepoznavanja posebnije vrste).
  const roditelji = new Map([...overrides].flatMap(([r, djeca]) => [...djeca].map((d) => [d, r])));
  const potomci = (id) => [...(overrides.get(id) || [])].flatMap((d) => [d, ...potomci(d)]);

  function pronadiRijeci(r) {
    const hits = [];
    for (let pos = 0; pos < r.length; pos++) {
      for (const { v, alias } of indeks.get(r[pos].slice(0, 3)) || []) {
        if (alias.every((a, j) => r[pos + j] && odgovara(r[pos + j], a))) hits.push({ id: v.id, pos, duzina: alias.length });
      }
    }
    return hits;
  }

  const opisne = new Set(["bio", "eko", "organsko", "organic", "premium", "mini", "maxi", "xxl", "xl", "domaci", "domaca", "domace", "svjezi", "svjeza", "svjeze", "trajno", "trajno", "snizeno", "pak", "pakirano", "pakirani", "svj", "smrznuti", "smrznuta", "smrznuto", "zamrznuti", "zamrznuta", "zamrznuto", "bijeli", "crni", "polubijeli", "razani", "integralni", "rezani", "tvrdi", "meki", "mladi", "trajni", "prirodni", "vocni", "100", "n", "fis"]);
  function analiziraj(tekst, marka = 0, upit = false, pripremljeneRijeci = null) {
    const r = pripremljeneRijeci || normaliziraj(tekst).split(" ").filter(Boolean);
    const hits = pronadiRijeci(r);
    // „s okusom”, „za kruh”, „od sira” opisuju sastojak ili namjenu.
    const boundary = r.findIndex((w) => prijedlozi.has(w));
    const heads = hits.filter((h) => boundary < 0 || h.pos < boundary || (h.pos === 0 && h.duzina > 1));
    heads.sort((a, b) => a.pos - b.pos || b.duzina - a.duzina);
    let glavni = heads[0] || null;
    // Razlog nerazvrstavanja (za reviziju): bez pojma, pojam samo iza prijedloga, nepoznate riječi prije pojma, pribor.
    let razlog = !hits.length ? "nijedan poznati pojam" : !glavni ? "pojam samo iza prijedloga" : "";
    // Nepoznate riječi prije glavne imenice mogu skrivati stvarnu vrstu.
    // Ne nagađaj da je sastojak (npr. mlijeko u kavi) glavni proizvod.
    if (glavni && !upit && r.slice(Math.max(0, Number(marka) || 0), glavni.pos)
      .some((w) => !opisne.has(w) && !/^\d/.test(w))) { glavni = null; razlog = "nepoznate riječi prije pojma"; }
    if (glavni && overrides.has(glavni.id)) {
      const special = hits.find((h) => overrides.get(glavni.id).has(h.id));
      if (special) glavni = special;
    }
    // Pribor nije materijal: "kanta za boju", "valjak za boju" nisu boja.
    const naziv = r.join(" ");
    if (glavni && ["boja", "boja-zid", "fasadna-boja"].includes(glavni.id)
      && /\b(valj\w*|kist\w*|kant\w*|posud\w*|spric\w*|pistolj\w*)\b/.test(naziv.split(" ").slice(0, glavni.pos).join(" "))) {
      glavni = null; razlog = "pribor, ne materijal";
    }
    const okusi = [...new Set(hits.filter((h) => voce.has(h.id)).map((h) => h.id))].sort();
    return { rijeci: r, hits, glavni, okusi, razlog: glavni ? "" : razlog };
  }

  function otisak(proizvodi) {
    let hash = 2166136261;
    for (const p of proizvodi) {
      const s = p[0] + "\x00" + p[1] + "\x00" + p[4] + "\n";
      for (let j = 0; j < s.length; j++) hash = Math.imul(hash ^ s.charCodeAt(j), 16777619);
    }
    return (hash >>> 0).toString(16).padStart(8, "0");
  }
  function pripremi(proizvodi, spremljeno = null, tokeni = null) {
    if (spremljeno && (spremljeno.verzija !== 1 || spremljeno.brojProizvoda !== proizvodi.length
      || spremljeno.otisak !== otisak(proizvodi))) throw new Error("Indeks skupina ne odgovara cjeniku");
    // Na mobitel šalji mali unaprijed pripremljeni indeks, bez analize svih naziva u memoriji.
    const analiza = spremljeno ? null : proizvodi.map((p) => analiziraj(p[0], p[4]));
    const dajAnalizu = (i) => analiza ? analiza[i] : analiziraj(proizvodi[i][0], proizvodi[i][4], false, tokeni?.[i]);
    const poVrsti = new Map();
    const katalog = new Map();
    const vrstePoRedu = new Array(proizvodi.length).fill(null);
    const dodaj = (id, naziv, i, roditelj = null) => {
      if (!katalog.has(id)) katalog.set(id, { id, naziv, roditelj, indeksi: [] });
      katalog.get(id).indeksi.push(i);
    };
    let nerazvrstano = 0;
    if (spremljeno) {
      for (const s of spremljeno.katalog) {
        katalog.set(s.id, s);
        if (!s.roditelj) {
          poVrsti.set(s.id, s.indeksi);
          for (const i of s.indeksi) {
            if (!Number.isInteger(i) || i < 0 || i >= proizvodi.length) throw new Error("Neispravan indeks proizvoda");
            vrstePoRedu[i] = s.id;
          }
        }
      }
      nerazvrstano = vrstePoRedu.filter((x) => !x).length;
    } else analiza.forEach((a, i) => {
      if (!a.glavni) { nerazvrstano++; return; }
      const id = a.glavni.id;
      vrstePoRedu[i] = id;
      if (!poVrsti.has(id)) poVrsti.set(id, []);
      poVrsti.get(id).push(i);
      dodaj(id, definicije.get(id).naziv, i);
      if (okusiVrste.has(id) && a.okusi.length) {
        const podid = id + "/" + a.okusi.join("+");
        dodaj(podid, definicije.get(id).naziv + " · " + a.okusi.map((x) => definicije.get(x).naziv).join(" + "), i, id);
      }
    });

    function razrijesiUpit(upit) {
      const q = analiziraj(upit, 0, true);
      if (!q.glavni) return null;
      const id = q.glavni.id;
      const aliasHit = q.hits.filter((h) => h.id === id).sort((a, b) => b.duzina - a.duzina)[0];
      const izostavi = new Set();
      if (aliasHit) for (let j = 0; j < aliasHit.duzina; j++) izostavi.add(aliasHit.pos + j);
      const trazeniOkusi = okusiVrste.has(id) ? q.okusi : [];
      if (trazeniOkusi.length) for (const h of q.hits) if (voce.has(h.id)) {
        for (let j = 0; j < h.duzina; j++) izostavi.add(h.pos + j);
      }
      const dodatno = q.rijeci.filter((w, j) => !izostavi.has(j) && !prijedlozi.has(w)).map(korijen);
      return { q, id, dodatno, trazeniOkusi };
    }
    function pogoci(upit) {
      const up = razrijesiUpit(upit);
      if (!up) return null; // Neprepoznati nazivi ostaju u postojećem pretraživanju.
      const {id, dodatno, trazeniOkusi} = up;
      // Odabir roditelja uključuje sve potomke (npr. „boja” → i boja za zidove, fasadna boja, temeljni premaz).
      const clanovi = [id, ...potomci(id)].flatMap((v) => poVrsti.get(v) || []);
      return clanovi.filter((i) => {
        const a = dajAnalizu(i);
        if (trazeniOkusi.length && a.okusi.join("+") !== trazeniOkusi.join("+")) return false;
        return dodatno.every((k) => a.rijeci.some((w) => odgovara(w, k)));
      });
    }
    // Moguća podudaranja nisu potvrđeni članovi skupine. Ostaju vidljiva za pregled.
    function moguciPogoci(upit) {
      const up = razrijesiUpit(upit);
      if (!up) return [];
      const aliasi = definicije.get(up.id).aliases;
      const nadji = [];
      for (let i = 0; i < proizvodi.length; i++) {
        if (vrstePoRedu[i]) continue;
        const rijeci = analiza ? analiza[i].rijeci : tokeni?.[i] || normaliziraj(proizvodi[i][0]).split(" ");
        const imaVrstu = aliasi.some((alias) => rijeci.some((_, p) => alias.every((k, j) => rijeci[p+j] && odgovara(rijeci[p+j], k))));
        if (!imaVrstu) continue;
        if (!up.dodatno.every((k) => rijeci.some((w) => odgovara(w, k)))) continue;
        const a = dajAnalizu(i);
        if (up.trazeniOkusi.length && a.okusi.join("+") !== up.trazeniOkusi.join("+")) continue;
        nadji.push(i);
      }
      return nadji;
    }
    return { pogoci, moguciPogoci, katalog: [...katalog.values()], nerazvrstano, ukupno: proizvodi.length,
      vrstaProizvoda: (i) => vrstePoRedu[i],
      izvezi: () => ({ verzija: 1, brojProizvoda: proizvodi.length, otisak: otisak(proizvodi), katalog: [...katalog.values()] }) };
  }
  // Svi istovrijedni nazivi; glasovni unos njima razdvaja nabrajanje bez zareza.
  const poznatiNazivi = zapis.split("\n").flatMap((r) => r.split("|")[2].split(";"));
  const api = { pripremi, analiziraj, poznatiNazivi, definicije: vrste.map(({id,naziv}) => ({id, naziv, roditelj: roditelji.get(id) || null})), potomci,
    nazivi: Object.fromEntries(zapis.split("\n").map((r) => [r.split("|")[0], r.split("|")[2].split(";")])) };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.Skupine = api;
})(typeof globalThis !== "undefined" ? globalThis : this);
