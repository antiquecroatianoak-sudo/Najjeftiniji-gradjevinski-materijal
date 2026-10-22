# Klasifikacija i filteri — stanje (21.10.2026.)

## Hijerarhija prema Njuškalu: blokirano
Izbornici https://www.njuskalo.hr/gradjenje-opremanje i https://www.njuskalo.hr/gradevinski-materijal dohvaćani su
skriptom `scripts/kategorije_njuskalo.py` na GitHub Actions (run 27): **HTTP 403 Forbidden** za obje stranice i za
`robots.txt`. Zabrana se ne zaobilazi, a dodatne razine se ne izmišljaju, pa hijerarhija prema Njuškalu još nije uvedena.
Kad bude dostupan stvarni popis kategorija, npr. vlasnik kopira izbornik iz preglednika, upisuje se kao roditelj → dijete
s URL-om i datumom provjere.

## Sadašnje stanje
- `site/skupine.js` ima 56 osnovnih vrsta (jedna razina). Proizvod bez prepoznate vrste nije izbačen: ostaje u pretrazi,
  označen „vrsta za provjeru“, i nije proglašen najpovoljnijim.
- Usporedba je uvijek unutar iste jedinice i specifikacije (`jedinica|spec`), pa se neusporedive specifikacije ne
  rangiraju zajedno.

## Revizija na stvarnom cjeniku (`scripts/revizija.cjs`, u svakom pokretanju radnog toka)
- Po izvoru se broje ponude, razvrstane i nerazvrstane ponude, s primjerima.
- Za svaku vrstu se provjerava da upit njezinim nazivom vraća **sve** njezine članove, i to u četiri inačice upita:
  obični, VELIKIM slovima, bez dijakritike i s velikim početnim slovom. Svaki gubitak se ispisuje s primjerima.
- Izvještaj: `site/data/revizija.json`.
- Brojke uvoza po fazi su u `stanje-izvora.json`: primljeno, prihvaćeno, nedostupno, odbačeno (bez cijene), zastarjelo,
  duplikati, neusporedeno.

## Run 36 (stvarni cjenik, 71 060 proizvoda)
- **74 vrste**, s vezom roditelj → dijete unutar ovog popisa vrsta (boja → boja za zidove, fasadna boja, temeljni premaz;
  ljepilo → ljepilo za pločice, za izolaciju; cijev → PVC cijev). Odabir roditelja uključuje potomke. To nije Njuškalova
  hijerarhija.
- **Razvrstano 16 420** (u runu 30 bilo je 2 611). Nerazvrstanih 54 640 ostaje u pretrazi kao „vrsta za provjeru“ i ne
  proglašava se najpovoljnijim.
- **Najčešće prve riječi nerazvrstanih** su JUB-ovi nazivi boja i fasada (jupol 18 132, jubizol 7 919, decor, jubin, takril,
  acrylcolor…; uglavnom Bačelićeve nijanse). Te marke nisu pridružene vrsti jer to zahtijeva potvrdu proizvođača.
- **Revizija:** nijedan razvrstan proizvod ne nestaje. Kombinirani filtri: 3 404 provjere (74 vrste × 46 kombinacija
  trgovina) bez gubitka, viška ili dvostrukih ponuda. Referentni uzorak: 1 od 1 000 nerazvrstanih nije bio dohvatljiv
  („List za pilu“ uz upit „list pilu“). Popravljeno: uz prepoznatu vrstu vraćaju se i nerazvrstani proizvodi sa svim
  riječima upita.
- **Njuškalo:** 403 za izbornike i robots.txt i u runu 36; hijerarhija prema Njuškalu nije ugrađena.
