# Izvori cijena — stanje provjere (20.10.2026.)

Uvoze se samo izvori koje je čovjek provjerio i uključio u `scripts/izvori.json`
(`"status": "provjereno"`, `"omogucen": true`). Trenutno **nijedan izvor nije uključen**,
pa aplikacija nema cjenik i ne objavljuje se. Nijedna cijena nije izmišljena.

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
| Gavroprom | trgovina | neprovjereno | Stranica i CSV od 21.10.2026. dostupni ChatGPT-u (3633 retka). Uvoz prilagođen stvarnom zaglavlju i retcima. Čeka puni uvoz stvarne datoteke. |
| Top Alati | trgovina | neprovjereno | CSV poslovnice Varaždin od 21.10.2026. dostupan ChatGPT-u (16834 retka, 2605 dostupno). Uvoz prilagođen stvarnom zaglavlju i retku. Čeka puni uvoz. |
| Veker | trgovina | neprovjereno | Stranica dostupna (200); arhivski XML s datumom u nazivu. Stupci XML-a još nisu viđeni. |
| Pevex | trgovina | blokirano | Službena stranica sidrene-cijene vodi na `store-3/aktualni.csv`; dohvat 403. |
| Bauhaus | trgovina | blokirano | Dohvat 403. Javni cjenik obvezan od 17.11.2026. |
| Bačelić | trgovina | blokirano | Stranica navodi CSV/XML; dohvat 403. |
| Arkor | trgovina | blokirano | Dohvat 403; URL cjenika nije potvrđen. |
| Profi baucentar | trgovina | neprovjereno | Dohvat 503; cjenik nije pronađen. |
| Vijci (Kralj commerce) | trgovina | neprovjereno | Dohvat 503; identitet nije provjeren. |
| IKOMA | trgovina | neprovjereno | Navedena stranica nije cjenik (prazna pretraga). |
| Fero-Term | trgovina | neprovjereno | Kandidat; URL i identitet nisu potvrđeni. |
| Petrokov | trgovina | neprovjereno | Kandidat; URL i identitet nisu potvrđeni. |
| Termometal | trgovina | neprovjereno | Kandidat; URL i identitet nisu potvrđeni. |
| Njuškalo | oglasnik | blokirano | Službeni API nije pronađen; automatsko prikupljanje bez dopuštenja se ne radi. |
| Index Oglasi | oglasnik | neprovjereno | Službeni API/izvoz nije pronađen; uvjeti nisu provjereni. |
| Plavi oglasnik | oglasnik | neprovjereno | Službeni API/izvoz nije pronađen; uvjeti nisu provjereni. |
| Facebook Marketplace | oglasnik | blokirano | Zahtijeva prijavu; prijave i CAPTCHA se ne zaobilaze. |

Popisano je 13 različitih trgovaca (poslovnice istog trgovca ne broje se zasebno). **Uključeno: 0.** Statusi 403/503 i
podaci o datotekama potječu iz ChatGPT-ova okruženja; iz ovog razvojnog okruženja svi ti hostovi su blokirani.

Ovo nije potpun popis hrvatskih trgovaca ni oglasnika.

## Uključivanje izvora (nakon 17.11.2026. ili uz dopuštenje oglasnika)
1. Otvoriti stranicu „Objava cjenika” trgovca, preuzeti CSV/XML web trgovine ili poslovnice i provjeriti stupce.
2. U `scripts/izvori.json` upisati `url`, `format`, po potrebi `"stupci"`, zatim `"status": "provjereno"`, `"omogucen": true`.
3. Lokalno: `python scripts/uvoz.py --lokalno id=datoteka.csv --datum id=GGGG-MM-DD` i pregledati `site/data/stanje-izvora.json`.

Izvor sa `"popis": true` i `"stranica"` čita stranicu s popisom datoteka (oblik naziva prema NN 101/2026:
`<vrsta>_<adresa>_<trgovac>_<oznaka>_<DD.MM.GGGG>_<HH.MM.SS>.csv`) i za svaku poslovnicu uzima najnoviju datoteku;
svaka poslovnica je zaseban izvor jer su cijene po poslovnici. `"poslovnice"` po potrebi ograničava na npr. web trgovinu.

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
