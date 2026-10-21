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
