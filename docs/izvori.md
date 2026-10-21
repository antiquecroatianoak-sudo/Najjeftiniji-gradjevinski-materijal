# Izvori cijena — stanje provjere (21.10.2026.)

Uvoze se samo izvori koje je čovjek provjerio i uključio u `scripts/izvori.json`
(`"status": "provjereno"`, `"omogucen": true`). Uključeno je **7 trgovaca**, svaki provjeren stvarnim uvozom cijele datoteke 21.10.2026.
Nijedna cijena nije izmišljena.

## Pravna osnova za trgovine
- Odluka o objavi cjenika proizvoda i usluga kao mjera izravne kontrole cijena, **NN 101/2026**
  (11.9.2026.), izmjena **NN 110/2026**: obveza vrijedi od **17.11.2026.** za sve trgovce na malo s mrežnom stranicom
  (ne samo hranu), u strojno čitljivom **CSV ili XML** obliku, zasebno za svaku poslovnicu i web trgovinu,
  dnevno do 8:00, dostupno 30 dana. Struktura datoteke nije propisana; pravilnik o sadržaju je najavljen.
  - https://www.zakon.hr/c/podzakonski-propis/1420946/nn-101-2026-%2811.9.2026.%29%2C-odluka-o-objavi-cjenika-proizvoda-i-usluga-kao-mjera-izravne-kontrole-cijena
  - https://narodne-novine.nn.hr/clanci/sluzbeni/2026_09_101_1213.html
  - https://www.teb.hr/novosti/2026/od-1102026-obveza-isticanja-dodatne-sidrene-cijene-i-objavi-cjenika-proizvoda-i-usluga/
  - https://digitalnicjenik.nepar.hr/vijesti/ministarstvo-pojasnjenja-digitalni-cjenik-sidrene-cijene-2026/
- Do tada je obveza (NN 75/2025) pokrivala samo hranu, piće, kozmetiku i kućanstvo, pa ne obuhvaća građevinski materijal.

Uvoz zato čita CSV i XML s uobičajenim nazivima stupaca (naziv, šifra, marka, MPC, jedinica mjere,
cijena za jedinicu mjere, posebna cijena, barkod), a za svaki izvor se mogu zadati vlastiti nazivi.

## Kako je provjeravano
Iz ovog razvojnog okruženja izravan pristup stranicama trgovaca i oglasnika nije bio moguć (mrežna pravila odbijaju
bauhaus.hr, pevex.hr, njuskalo.hr, index.hr, plavi-oglasnik.hr; ni dohvat stranica preko alata nije radio).
Stanje je utvrđeno samo web pretragom. Zato nijedan URL cjenika nije potvrđen.

| Izvor | Vrsta | Stanje | Što je utvrđeno (21.10.2026.) |
|---|---|---|---|
| Gavroprom | trgovina | **uključeno** | Stvarni uvoz 21.10.2026.: 3633 primljeno, 2129 prihvaćeno, 1504 nedostupno; datum iz naziva datoteke. |
| Top Alati | trgovina | **uključeno** | Stvarni uvoz poslovnice Varaždin 21.10.2026.: 16834 primljeno, 2605 prihvaćeno, 14229 nedostupno. Poslovnice su zasebni izvori, ali jedan trgovac. |
| Veker | trgovina | **uključeno** | Stvarni uvoz XML-a 21.10.2026.: 3791 primljeno, 3712 prihvaćeno, 79 nedostupno; datum iz `generirano`. |
| Pevex | trgovina | blokirano | Službena stranica sidrene-cijene vodi na `store-3/aktualni.csv`; dohvat 403. |
| Bauhaus | trgovina | blokirano | Dohvat 403. Javni cjenik obvezan od 17.11.2026. |
| Bačelić | trgovina | blokirano | Stranica navodi CSV/XML; dohvat 403. |
| Arkor | trgovina | blokirano | Dohvat 403; URL cjenika nije potvrđen. |
| Profi baucentar | trgovina | **uključeno** | Javni `sidrena-cijena.xml` (profibaucentar.hr): 2017 primljeno, 1543 prihvaćeno, 474 nedostupno; datum iz `generated`. |
| Vijci (Kralj commerce) | trgovina | neprovjereno | Dohvat 503; identitet nije provjeren. |
| IKOMA | trgovina | neprovjereno | Navedena stranica nije cjenik (prazna pretraga). |
| Fero-Term | trgovina | neprovjereno | fero-term.hr dostupna (200); cjenik nije pronađen. |
| Petrokov | trgovina | neprovjereno | petrokov.hr dostupna (200); cjenik nije pronađen. |
| TERMO-METAL (Pakrac) | trgovina | **uključeno** | Stvarni uvoz 21.10.2026.: 3381 primljeno, 3115 prihvaćeno, 266 nedostupno; datum iz naziva datoteke. |
| Termometal (Garešnica) | trgovina | neprovjereno | Drugi trgovac (termometal.hr); cjenik nije pronađen. |
| Akord Županja | trgovina | neprovjereno | akord-zupanja.hr/cjenik — službena stranica cjenika; datoteke još nisu viđene. |
| Građevinska apoteka | trgovina | **uključeno** | Stalni `sidrena-cijena.xml`: 292 proizvoda, 286 prihvaćeno, 3 nedostupno; datum iz `generated` (UTC → Zagreb). |
| Gradnja invest | trgovina | neprovjereno | CSV u podnožju kataloga; datoteka još nije viđena. |
| Telack | trgovina | **uključeno** | Stalni `cjenik-webshop.xml`: 470 primljeno, 470 prihvaćeno; datum iz `datum` (DD.MM.GGGG). |
| Mirakul inovativna grijanja | trgovina | neprovjereno | XML u podnožju; oprema za grijanje. |
| EraCommerce | trgovina | neprovjereno | Službena domena i identitet nisu potvrđeni (pretraga 21.10.2026. nije našla vezu s građevinskim materijalom); URL se ne nagađa. |
| Njuškalo | oglasnik | blokirano | Službeni API nije pronađen; automatsko prikupljanje bez dopuštenja se ne radi. |
| Index Oglasi | oglasnik | neprovjereno | Službeni API/izvoz nije pronađen; uvjeti nisu provjereni. |
| Plavi oglasnik | oglasnik | neprovjereno | Službeni API/izvoz nije pronađen; uvjeti nisu provjereni. |
| Facebook Marketplace | oglasnik | blokirano | Zahtijeva prijavu; prijave i CAPTCHA se ne zaobilaze. |

Popisano je 19 različitih trgovaca (poslovnice istog trgovca ne broje se zasebno). **Uključeno: 7** (Gavroprom, Top Alati, Veker, TERMO-METAL, Građevinska apoteka, Telack, Profi baucentar); ostalih 12 nije aktivno. Statusi 403/503, brojke stvarnog uvoza i
podaci o datotekama potječu iz ChatGPT-ova okruženja (verzije 44655df i e7df3c9); iz ovog razvojnog okruženja ti hostovi su blokirani.

Ovo nije potpun popis hrvatskih trgovaca ni oglasnika.

## Automatsko otkrivanje (`scripts/otkrivanje.py`, svaki dan u GitHub Actions)
1. **Polazne domene**: službene domene iz `izvori.json` i `scripts/domene.json` (jedan unos po trgovcu; `www.` i
   poddomene istog trgovca nisu različiti trgovci; ručno uključeni izvori se ne otkrivaju ponovno).
2. **Otkrivanje** na svakoj domeni: poveznice s naslovne stranice prema stranicama cjenika i uobičajene putanje
   (`/cjenik/`, `/cjenici/`, `/sidrene-cijene/`, `/prices-list`, `/sidrena-cijena.xml`, `/cjenik.xml`). Stranica s
   datiranim datotekama postaje kandidat "popis", stalna datoteka kandidat "stalni". Poštuje se `robots.txt`;
   403/404 se ne zaobilaze i ne ponavljaju.
3. **Provjera**: kandidat se preuzme i uveze istim uvozom: datum objave (≤ 3 dana), barem 20 valjanih ponuda, dostupnost,
   jedinice. Dokaz (URL, datum, broj primljenih/prihvaćenih/nedostupnih, s jedinicom, vrijeme provjere) ili razlog
   odbijanja zapisuje se u `site/data/otkriveni.json` (objavljuje se uz aplikaciju).
4. **Uključivanje**: prihvaćeni kandidati ulaze u isti dan u uvoz (`uvoz.py --otkriveni`).
5. **Ograničenje**: bez API ključa tražilice nove *domene* ne otkrivaju se same; dodaje ih čovjek u `domene.json`.
   Plaćena usluga nije uvedena.

## Dnevni rad i pouzdanost
- Dohvat: timeout 60 s, do 3 pokušaja uz rastuće čekanje (403/404 bez ponavljanja); greška jednog izvora ne ruši ostale.
- Zadnji valjani cjenik svakog izvora čuva se (`.predmemorija`, GitHub Actions cache). Kad izvor ne radi, koristi se taj
  cjenik s **izvornim datumom** i oznakom `iz_predmemorije`; stariji od 3 dana se ne uvozi.
- Novi `proizvodi.json` zamjenjuje stari tek nakon provjere (atomska zamjena); bez valjanih cjenika objava se preskače.
- Izvještaj u sažetku pokretanja: broj trgovaca, poslovnica, ponuda i izvora iz predmemorije.
- Radni tok je napisan; **raspored radi tek nakon spajanja na `main` i uključivanja GitHub Pagesa**, a nijedan
  produkcijski run još nije pokrenut.

## Uključivanje izvora (nakon 17.11.2026. ili uz dopuštenje oglasnika)
1. Otvoriti stranicu „Objava cjenika” trgovca, preuzeti CSV/XML web trgovine ili poslovnice i provjeriti stupce.
2. U `scripts/izvori.json` upisati `url`, `format`, po potrebi `"stupci"`, zatim `"status": "provjereno"`, `"omogucen": true`.
3. Lokalno: `python scripts/uvoz.py --lokalno id=datoteka.csv --datum id=GGGG-MM-DD` i pregledati `site/data/stanje-izvora.json`.

Izvor sa `"popis": true` i `"stranica"` čita stranicu s popisom datoteka (oblik naziva prema NN 101/2026:
`<vrsta>_<adresa>_<trgovac>_<oznaka>_<DD.MM.GGGG>_<HH.MM.SS>.csv`) i za svaku poslovnicu uzima najnoviju datoteku;
svaka poslovnica je zaseban izvor jer su cijene po poslovnici. Broj pohrane (zadnji broj prije datuma, raste sa svakom
objavom) ne ulazi u oznaku poslovnice, pa stare datoteke ne postaju lažne poslovnice. `"poslovnice"` po potrebi ograničava na npr. web trgovinu.

Datum cjenika je datum objave koji navodi izvor, nikad vrijeme preuzimanja. Cjenik bez datuma ili stariji od 3 dana ne uvozi se
(`stanje-izvora.json` navodi razlog), a datum u aplikaciji je najstariji uključeni cjenik. Isti barkod s različitom
količinom, jedinicom ili specifikacijom u dva izvora ne spaja se u jednu ponudu.

## Pravila za retke trgovaca
- Redak s `dostupnost` = nedostupan ne uvozi se (broji se u `nedostupno`).
- "KOM" bez poznatog sadržaja (npr. „GLET MASA 25/1”) ostaje vidljiv bez poretka, osim kad specifikacija (dimenzije, promjer, razred) određuje komad.
- `sidrena_cijena` i `sidrena_cijena_od` nisu trenutna cijena ni datum cjenika.

## Oglasi: oblik `oglasi-json`
Popis objekata: `id, naziv, cijena, valuta, cijenaNaUpit, pregovaranje, kolicina, jedinica (kg/l/m/m2/m3/kom),
specifikacija, stanje (novo/rabljeno), pdv (ukljucen/nije-obveznik), lokacija, dostava, url, provjereno (ISO datum), aktivno, prodano`.
- Rangira se samo oglas s cijenom u EUR, poznatom količinom i jedinicom, specifikacijom, stanjem i jasnim PDV-om.
- Ostali se prikazuju kao „Nije uspoređeno: razlog” i nikad nisu najpovoljniji.
- Oglas bez cijene (na upit) nema iznos i ne prikazuje se. Prodani, neaktivni i oglasi provjereni prije više od 7 dana se uklanjaju.
- Isti oglas na više oglasnika (isti naslov, cijena i mjesto) prikazuje se jednom.
- Svaki oglas čuva izvor, URL i datum provjere.
