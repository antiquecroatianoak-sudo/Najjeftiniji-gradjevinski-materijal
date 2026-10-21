# Izvori cijena — stanje provjere (21.10.2026.)

Uvoze se samo izvori koje je čovjek provjerio i uključio u `scripts/izvori.json`
(`"status": "provjereno"`, `"omogucen": true`). Uključeno je **7 trgovaca**, svaki provjeren stvarnim uvozom cijele datoteke 21.10.2026.
Nijedna cijena nije izmišljena.

## Stvarno pokretanje na GitHub Actions (21.10.2026., run 23, commit 2696c2b, grana bez objave)
Isti rezultat kao run 19 (a7120f3). Run 22 (df86130): TERMO-METAL je vratio 403 → 7 trgovaca; u produkciji bi se tada koristio zadnji valjani cjenik iz predmemorije (ako nije stariji od 3 dana).
Otkrivanje i uvoz izvršeni na GitHubovim poslužiteljima (koji, za razliku od razvojnog okruženja, imaju pristup internetu):
**8 različitih trgovaca, 10 poslovnica/izvora, 34 399 jedinstvenih proizvoda (ne ponuda; vidi „Brojke”), svi cjenici od 2026-10-21.**

| Trgovac | URL (najnovija datoteka) | Primljeno | Prihvaćeno | Nedostupno |
|---|---|---|---|---|
| Bačelić (web trgovina, otkriveno automatski) | bacelic.hr/cjenici/internet-trgovina_…_21.10.2026_07.46.50.266.csv | 55 703 | 46 967 | 8 735 |
| Top Alati (3 poslovnice) | top-alati.hr/user-content/cjenici/2026-10-21/… (Čakovec, Varaždin, Prelog) | 3 × 16 834 | 2 574 / 2 605 / 9 347 | 14 260 / 14 229 / 7 487 |
| Veker | veker.hr/wp-content/uploads/cjenici-webshop/cjenik.xml | 3 791 | 3 712 | 79 |
| TERMO-METAL (Pakrac) | termo-metal.hr/sidrena/cjenik/…_20261021-0110.xml | 3 381 | 3 115 | 266 |
| Gavroprom | gavroprom.hr/cjenici/…_21.10.2026_07.45.09.153.csv | 3 633 | 2 129 | 1 504 |
| Profi baucentar | profibaucentar.hr/sidrena-cijena.xml | 2 017 | 1 543 | 474 |
| Telack | telack.shop/cjenik/cjenik-webshop.xml | 470 | 470 | 0 |
| Građevinska apoteka | gradjevinska-apoteka.hr/sidrena-cijena.xml | 289 | 286 | 3 |

Odbačeno uz razlog: Bačelić prodavaonice (4) — „nema dostupnih ponuda“ (svi retci nedostupni); Top Alati stare datoteke od
27.09.2026. — zastarjele; Akord Županja i Gradnja invest — datoteka nije valjan XML; termometal.hr — prazna datoteka;
Unikomerc — nepoznat datum cjenika; Pevex, Bauhaus, IKOMA, Vijci, Fero-Term, Petrokov, Mirakul, Građa.hr — cjenik nije
pronađen ili je pristup odbijen. Nakon popravka „soft 404“ (run 22+) Akord, Gradnja invest i ERA više nisu greška
obrade nego „cjenik nije pronađen“: na uobičajenim putanjama vraćaju HTML stranicu, a na naslovnoj nema poveznice na
CSV/XML. Imenik sidrocjenici.com (119 KB, 69 poveznica, 0 vanjskih, 23 podstranice) dao je 4 nove domene (rif.hr,
vasatrgovina.hr, primjer.hr, azop.hr) — nijedna nema cjenik; popis trgovaca u imeniku nije dostupan u HTML-u.
**Cilj od najmanje 11 različitih trgovaca nije postignut (8).**

## Stvarno pokretanje run 36 (commit 2fcac48, kod do 00cab7d, 21.10.2026., grana bez objave)
https://github.com/antiquecroatianoak-sudo/Najjeftiniji-gradjevinski-materijal/actions/runs/39632787720

**13 različitih trgovaca:** 8 sa službenim CSV/XML cjenikom (Bačelić, Top Alati, Veker, TERMO-METAL, Gavroprom, Profi
baucentar, Telack, Građevinska apoteka, ARKOR; ARKOR i Bačelić otkriveni automatski) i 5 iz pilota sa stranica proizvoda.
Ukupno 15 izvora, 71 060 jedinstvenih proizvoda. Brojke: ulaznih redaka 343 527, prihvaćenih 71 112, spojeno u izvoru 42,
ponuda proizvod×izvor 71 070.

**Pilot webshopova (schema.org Product/Offer, 25 stranica po trgovcu po pokretanju):**

| Trgovac | Ponuda | Potpune (rangiraju se) | Napomena |
|---|---|---|---|
| Građa.hr (gradja.hr) | 18 | 18 po podacima ponude; 3 s prepoznatom količinom | PDV uključen (schema.org) |
| MC PLUS (mc-plus.hr) | 18 | 18; 10 s prepoznatom količinom | PDV iz teksta stranice; 5 nedostupnih isključeno |
| ERA-COMMERCE (era-commerce.hr) | 25 | 0 | PDV nije naveden → vidljivo, ne rangira se |
| Frida Mijić (frida-mijic.hr) | 3 | 0 | PDV nije naveden; 5 stranica nedohvatljivo |
| Consortium (consortium.hr) | 7 | 0 | raspon cijena (varijante); među njima i testni proizvodi trgovca („test“) |
| Merkury, Fero-Term, Drvona, Petrokov, Akord | 0 | — | stranice bez schema.org ponude u EUR |
| IKOMA, Bit Promet, Gradnja invest | 0 | — | sitemap sa stranicama proizvoda nije pronađen |

Ponude iz pilota imaju vrijeme provjere, ne datum objave. Na glavnoj grani pilot nije uključen dok se ne pregleda.

**Spajanje redaka (stvarni sirovi uzorak):** Bačelić je imao 36 454 retka s barkodom „0“ spojena u jedan proizvod, popravljeno
u bafd7c2; u runu 36 Bačelić ima 0 spojenih i 46 967 ponuda. Veker i ARKOR imaju istu šifru za različite boje ili veličine
(npr. „Škare PROLINE“ 31,99/46,99/64,99/88,99 €; DASSY kombinezon s i bez marke po različitoj cijeni). Od commita nakon
run 36 takvi retci ostaju zasebne ponude; spajaju se samo potpuno isti retci (isti naziv i cijena). Isti pravi EAN i dalje
označava isti artikl.

## Izvještaj po trgovcu — run 27 (commit 56333cb, 21.10.2026., grana bez objave)
https://github.com/antiquecroatianoak-sudo/Najjeftiniji-gradjevinski-materijal/actions/runs/39593507440 —
**9 različitih trgovaca, 11 izvora, 35 794 jedinstvenih proizvoda (ne ponuda; vidi „Brojke”)**, svi cjenici od 2026-10-21. Cijene su u EUR s PDV-om (maloprodajne,
NN 101/2026). Jedinica, pakiranje i specifikacija dolaze iz cjenika i naziva.

| Trgovac | Službeni URL | Status | Dokaz / razlog | Prihvaćeno |
|---|---|---|---|---|
| ARKOR (Imotski) | arkor.hr | **aktivan (otkriveno)** | arkor.hr/sidrena/cjenik/internet-trgovina_…_20261021-0010.xml | 1 408 |
| Bačelić, Top Alati, Veker, TERMO-METAL, Gavroprom, Profi baucentar, Telack, Građevinska apoteka | vidi gore | **aktivan** | stvarni dohvat 21.10.2026. | 34 386 |
| IKOMA | ikoma.hr | kandidat | cijene samo na HTML stranicama webshopa, nema CSV/XML | — |
| Fero-Term | fero-term.hr | kandidat | isto (HTML webshop) | — |
| Petrokov | petrokov.hr | kandidat | isto | — |
| Akord Županja | akord-zupanja.hr | kandidat | isto | — |
| ERA-COMMERCE | era-commerce.hr | kandidat | identitet potvrđen (OIB 28609792467); HTML webshop, nema CSV/XML | — |
| Građa.hr | gradja.hr | kandidat | HTML webshop | — |
| Frida Mijić | frida-mijic.hr | kandidat | HTML webshop | — |
| Consortium | consortium.hr | kandidat | HTML webshop | — |
| Merkury | merkury.hr | kandidat | HTML webshop (/mort/, /zbuka/ su kategorije istog trgovca) | — |
| MC PLUS | mc-plus.hr | kandidat | HTML webshop | — |
| Bit Promet | bitpromet.hr | kandidat | cjenik nije pronađen | — |
| Drvona | drvona.hr | kandidat | cjenik nije pronađen | — |
| Gradnja invest | katalog.gradnjainvest.hr | kandidat | cjenik nije pronađen | — |
| Unikomerc | unikomerc-uvoz.hr | kandidat | datoteka bez datuma objave | — |
| Termometal (Garešnica) | termometal.hr | kandidat | prazna XML datoteka | — |
| Pevex | pevex.hr | blokiran | 403 na naslovnoj | — |
| Bauhaus | bauhaus.hr | blokiran | 403 | — |
| Mirakul | mirakul-inovativna-grijanja.hr | blokiran | 403 | — |
| Vijci | vijci.com | blokiran | TLS certifikat se ne može provjeriti (provjera se ne isključuje) | — |

Imenici (samo otkrivanje, ne izvor cijena): sidrocjenici.com → 4 domene, nijedan trgovac; ecroatia.info (Zagreb,
građevinski materijali; 543 poveznice, 60 podstranica) → 3 vanjske domene, sve nevezane (agencija, portal);
gradim.hr → bez vanjskih trgovaca. Kalcer, Altum i Gratis nisu pronađeni kao vanjske poveznice ni domene u imeniku,
pa nisu provjereni (domena se ne nagađa). Google pretraga se ne dohvaća automatski (uvjeti korištenja); kandidati iz nje
dodani su ručno u `domene.json`.

**Webshopovi bez CSV/XML**: 10 trgovaca ima cijene samo na HTML stranicama. Uvoz cijena s HTML stranica (npr. strukturirani
podaci schema.org/Product) nije uveden jer mijenja dosadašnje pravilo „samo službeni strojno čitljivi cjenici“; čeka
odluku. Obveza objave CSV/XML za sve trgovce počinje 17.11.2026.

## Brojke (od commita nakon 2121705)
Raniji izvještaji zvali su broj redaka u `proizvodi.json` „ponudama“. To je zapravo broj **jedinstvenih proizvoda**, pa je
zato bio manji od Bačelićevih 46 967 prihvaćenih redaka. Sada se odvojeno broji i provjerava:
- **ulazni redak**: redak datoteke;
- **prihvaćeni redak**: dostupan, s cijenom, u opsegu;
- **spojeno u izvoru**: isti proizvod (barkod ili šifra, ista mjera i specifikacija) više puta u istom cjeniku, zadržava se niža cijena;
- **ponuda proizvod×izvor** = prihvaćeni redci − spojeni u izvoru, a mora biti jednaka zbroju `ponuda_u_aplikaciji` po izvoru;
- **jedinstveni proizvod**: isti proizvod kroz sve izvore je jedan red u aplikaciji, s cijenom svakog izvora.
Neusklađeni brojevi zaustavljaju objavu. Sve se zapisuje u `stanje-izvora.json` → `brojke` i ispisuje u sažetku runa.

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
| EraCommerce | trgovina | identitet potvrđen | ERA-COMMERCE d.o.o., Makarska, OIB 28609792467 (Fina info.BIZ, CompanyWall); domena era-commerce.hr, građevinski materijal, alati i oprema za dom. Dodana u `domene.json`; cjenik se otkriva i provjerava automatski, URL se ne nagađa. |
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
5. **Nove domene bez ručnog upisa**: javni imenici/agregatori cjenika iz `domene.json` → `"imenici"` (sada
   sidrocjenici.com) čitaju se svaki dan; svaka vanjska `.hr` domena koja nije poznata, nije platforma (društvene mreže,
   tražilice, alati) i nije sam imenik postaje novi kandidat (najviše 80 po pokretanju), uključujući domene navedene u tekstu ili ugrađenom JSON-u imenika i na njegovim podstranicama (do 60). Uz istu provjeru kao gore mora
   proći i **provjeru asortimana**: barem 10 % naziva s građevinskim pojmom (cement, ljepilo, cijev, vijak, alat…), inače
   „asortiman nije građevinski“. **Identitet/duplikat**: domena se svodi na trgovca (bez `www.`), a dvije domene s istim
   naslovom stranice i istim brojem ponuda prihvaćaju se kao jedan trgovac. Neobradiva datoteka bilježi se s kratkim
   uzorkom početka (dijagnoza).
6. **Ograničenje**: domene koje nisu ni u jednom javnom imeniku ni u `domene.json` ne mogu se pronaći bez tražilice;
   za to bi trebao API ključ tražilice (npr. Bing/Google Programmable Search), koji nije uveden. Plaćena usluga nije uvedena.

## Dnevni rad i pouzdanost
- Dohvat: timeout 60 s, do 3 pokušaja uz rastuće čekanje (403/404 bez ponavljanja); greška jednog izvora ne ruši ostale.
- Zadnji valjani cjenik svakog izvora čuva se (`.predmemorija`, GitHub Actions cache). Kad izvor ne radi, koristi se taj
  cjenik s **izvornim datumom** i oznakom `iz_predmemorije`; stariji od 3 dana se ne uvozi.
- Novi `proizvodi.json` zamjenjuje stari tek nakon provjere (atomska zamjena); bez valjanih cjenika objava se preskače.
- Izvještaj u sažetku pokretanja: broj trgovaca, poslovnica, ponuda i izvora iz predmemorije.
- **Napisani raspored**: `cron: "37 7 * * *"` (UTC, tj. 9:37 po hrvatskom ljetnom / 8:37 zimskom vremenu) u `.github/workflows/dnevno-azuriranje.yml`, posao `azuriraj-i-objavi`.
- **Aktivni produkcijski raspored: NE** — GitHub pokreće `schedule` samo sa zadane grane (`main`); kod je na grani PR #1.
- **Uspješan produkcijski run: NIJEDAN.** Postoje samo provjere na grani (posao `provjera-izvora`, bez objave).
- Za aktivaciju (tek nakon neovisne provjere): Settings → Pages → Source: **GitHub Actions**; spojiti PR #1 na `main`;
  ručno pokrenuti radni tok (Actions → Dnevno ažuriranje cijena → Run workflow) i provjeriti sažetak i objavljenu stranicu.

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
