# Podudarnost s aplikacijom Najjeftinija košarica

Izvor usporedbe: `antiquecroatianoak-sudo/Najjeftinija-kosarica`, grana `claude/dreamy-hopper-f6e4u0` (28e37c2),
s ispravkom usporedbe količina iz PR #5. Izgled (raspored, ikone, veličine, fontovi, boje) preuzet je
nepromijenjen iz produkcije, uključujući pregledane crvene rubove žutih ploha iz PR #6 (oba spojena 20.10.2026., 48410d8) i PR #8
(istaknuti iznos trgovine = zbroj njezinih kartica, cijela pakiranja; iznos po jedinici je sporedan i označen).

| Funkcija u izvornoj aplikaciji | Ovdje | Provjera |
|---|---|---|
| Popis za kupnju kao glavni prikaz | da | Playwright, 320/390/1280 px |
| Glasovni unos: jedan pritisak = jedan artikl, odmah spremljen, bez automatskog ponovnog pokretanja | da, isti kod | `tests/glasovni-unos.cjs` |
| Ručni unos i nabrajanje više artikala | da; decimalni zarez („2,5 m2”) nije razdjelnik | `tests/kosarica.cjs` |
| Količine (+/−), brisanje, oznaka „u košarici”, napredak | da; uz izgovorenu mjeru +/− mijenja m²/m³/kg za 1 | Playwright |
| Spremanje popisa na uređaju | da (`gradjevina-v1`, odvojeno od košarice) | — |
| Automatsko razvrstavanje u skupine i pretraga po nazivu | da, s pravilima za građevinski materijal (pribor ≠ materijal, npr. valjak ≠ boja) | `tests/skupine.cjs` |
| Poredak po jediničnoj cijeni, alternative (sljedeći/prethodni) | da; jedinice kg, l, kom, **m, m², m³**; usporedba samo unutar iste specifikacije | `tests/kosarica.cjs`, `tests/uvoz.py` |
| Moguća podudaranja s nejasnom vrstom, bez proglašenja najpovoljnijeg | da | — (isti kod) |
| Odabir i isključivanje trgovina (Sve / Nijedna) | da; trgovine prije oglasnika | Playwright |
| Najpovoljnija kombinacija svih trgovina, iznos po trgovinama | da | Playwright, `tests/kosarica.cjs` |
| Cijela košarica u jednoj trgovini | da; promjena trgovine čuva traženu količinu, cijela pakiranja | `tests/kosarica.cjs` |
| Označavanje nepotpunih košarica i stavki bez cijene | da | `tests/kosarica.cjs` |
| Stanje podataka, datum, „Pokušaj ponovno”, rad bez interneta | da (service worker `gradjevina-v1`) | Playwright (prazni podaci) |
| Dnevni automatski uvoz i objava | radni tok postoji; **ne radi dok nijedan izvor nije provjeren** — tada preskače objavu | `.github/workflows/dnevno-azuriranje.yml` (nije pokrenut) |

## Novo za građevinski materijal
- Izgovorena količina: „20 m2 laminata”, „2,5 kubika betona”, „2 tone pijeska” → tražena količina; računaju se cijela pakiranja za barem tu količinu u svakoj trgovini.
- Specifikacija (EPS razred, debljina, CEM razred, C2TE, Ø, dimenzije) odvaja neusporedive proizvode.
- Oglasi: stanje, lokacija, datum provjere i poveznica na izvor; nepotpuni oglasi su „Nije uspoređeno: razlog”.

## Nije provjereno / ograničenja
- Nema stvarnih podataka: nijedan izvor nije potvrđen (vidi `docs/izvori.md`), pa ni automatsko ažuriranje nije testirano na stvarnim cjenicima.
- Prepoznavanje specifikacija i količina testirano je na sintetičkim nazivima; stvarni cjenici će tražiti dorade pravila.
- Cijena je najniža u trgovini (svim poslovnicama); lokacija poslovnice i dostava nisu uključeni u usporedbu.
- Glasovni unos ostaje „jedan artikl po pritisku” kao u produkciji (kontinuirano nabrajanje je vraćeno u izvornoj aplikaciji 851a3d2).
