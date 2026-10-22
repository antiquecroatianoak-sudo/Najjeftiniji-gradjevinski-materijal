# Najjeftiniji građevinski materijal

Web aplikacija (PWA) za usporedbu cijena građevinskog materijala i opreme u hrvatskim trgovinama i oglasnicima.
Zaseban projekt, s istim funkcijama kao [Najjeftinija košarica](https://github.com/antiquecroatianoak-sudo/Najjeftinija-kosarica)
i vlastitim poslovnim izgledom; ne dijeli podatke s njom.

**Cilj aplikacije** (potvrdio korisnik): [docs/cilj-aplikacije.md](docs/cilj-aplikacije.md). Pri planiranju, implementaciji i
pregledu svake promjene provjeriti služi li tom cilju. Dostavu nude i obavljaju trgovine. Povezivanje s njihovom dostavom,
uz izvor i datum provjere podataka sa službenih stranica i razlikovanje potvrđenih od nepoznatih uvjeta, budući je smjer
razvoja i još nije implementirano.

1. Složi popis glasom ili upisom: „20 m2 laminata, 3 vreće cementa, stiropor”.
2. Za svaku stavku vidiš najpovoljniju ponudu po m², m³, m, kg, l ili komadu, samo među proizvodima iste specifikacije.
3. Usporedi cijeli popis po trgovinama ili kupi sve u jednoj; cijena se računa za cijela pakiranja.

**Stanje:** 7 trgovaca uključeno ručno nakon stvarnog uvoza (Gavroprom, Top Alati, Veker, TERMO-METAL,
Građevinska apoteka, Telack, Profi baucentar), a Bačelić i ARKOR otkriveni su automatski (9 ukupno, vidi docs/izvori.md); ostali su popisani
s pravim stanjem u [docs/izvori.md](docs/izvori.md). Trgovci s mrežnim stranicama moraju dnevno objavljivati strojno čitljive cjenike (XML ili CSV) od 1.10.2026.
(NN 101/2026). Popis funkcija: [docs/paritet.md](docs/paritet.md).

Dnevni rad (GitHub Actions): automatsko otkrivanje javnih cjenika na službenim domenama, provjera i uključivanje,
uvoz svih provjerenih izvora uz zadnji valjani cjenik za izvor koji ne radi, atomska objava. Detalji u docs/izvori.md.

## Razvoj
```
python3 tests/uvoz.py && python3 tests/otkrivanje.py
node tests/skupine.cjs && node tests/kosarica.cjs && node tests/glasovni-unos.cjs
python3 scripts/uvoz.py --lokalno id=cjenik.csv   # izvor mora biti provjeren u scripts/izvori.json
node scripts/razvrstaj.cjs
```
Objava (GitHub Pages) radi samo s glavne grane i samo kad postoji uvezen cjenik.
