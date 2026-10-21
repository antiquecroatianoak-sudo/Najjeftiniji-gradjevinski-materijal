# Najjeftiniji građevinski materijal

Web aplikacija (PWA) za usporedbu cijena građevinskog materijala i opreme u hrvatskim trgovinama i oglasnicima.
Zaseban projekt, s istim izgledom i funkcijama kao [Najjeftinija košarica](https://github.com/antiquecroatianoak-sudo/Najjeftinija-kosarica);
ne dijeli podatke s njom.

1. Složi popis glasom ili upisom: „20 m2 laminata, 3 vreće cementa, stiropor”.
2. Za svaku stavku vidiš najpovoljniju ponudu po m², m³, m, kg, l ili komadu, samo među proizvodima iste specifikacije.
3. Usporedi cijeli popis po trgovinama ili kupi sve u jednoj; cijena se računa za cijela pakiranja.

**Stanje:** uključena su 3 trgovca provjerena stvarnim uvozom (Gavroprom, Top Alati, Veker); ostali su popisani
s pravim stanjem u [docs/izvori.md](docs/izvori.md). Trgovci moraju objavljivati strojno čitljive cjenike od 17.11.2026.
(NN 101/2026, NN 110/2026). Popis funkcija: [docs/paritet.md](docs/paritet.md).

## Razvoj
```
python3 tests/uvoz.py
node tests/skupine.cjs && node tests/kosarica.cjs && node tests/glasovni-unos.cjs
python3 scripts/uvoz.py --lokalno id=cjenik.csv   # izvor mora biti provjeren u scripts/izvori.json
node scripts/razvrstaj.cjs
```
Objava (GitHub Pages) radi samo s glavne grane i samo kad postoji uvezen cjenik.
