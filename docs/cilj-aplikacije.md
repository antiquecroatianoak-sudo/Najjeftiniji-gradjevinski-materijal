# Cilj aplikacije

Potvrdio korisnik 21. listopada 2026. Ovo je stalna polazna osnova za daljnji razvoj građevinske aplikacije. Pri planiranju, implementaciji i pregledu svake sljedeće promjene treba se vratiti ovom cilju i provjeriti služi li mu promjena.

Povezati kupce s najjeftinijom odgovarajućom ponudom građevinskog materijala i opreme iz različitih dućana te im omogućiti jasan izbor između:

1. Najpovoljnije kombinacije kupnje u više dućana.
2. Kupnje cijelog istog popisa u jednom najpovoljnijem dućanu, uz vidljiv prikaz ukupnih cijena ostalih dućana.

Usporedbe moraju zadržati iste tražene količine i usporedive specifikacije, računati potrebna cijela pakiranja te jasno razlikovati potpune od nepotpunih ponuda. Najpovoljnija potpuna opcija mora biti jasno označena.

## Povezivanje s dostavom trgovina

Dostavu nude i obavljaju same trgovine. Aplikacija treba uz određenu trgovinu povezati njezinu postojeću mogućnost dostave s ponudom robe i omogućiti kupcu prijelaz na naručivanje ili upit kod te trgovine. Aplikacija ne preuzima organizaciju vlastite dostavne službe.

Prikazati provjerene podatke o dostupnosti dostave za lokaciju kupca, području dostave, cijeni ili načinu obračuna, minimalnoj narudžbi, rokovima i ograničenjima za vrstu/količinu robe, kad su ti podaci dostupni. Nepoznate uvjete jasno označiti kao nepotvrđene; nepoznata cijena nije besplatna dostava. Ne tvrditi da postoji partnerstvo ili aktivna integracija bez potvrde.

Kad je trošak dostave potvrđen za konkretnu narudžbu i lokaciju, prikazati cijenu robe i dostavu odvojeno te njihov ukupni iznos radi usporedbe. Kupnju iz više trgovina računati s odgovarajućim dostavama svake od njih.

Ovo je dogovoreni smjer budućeg razvoja. Konkretne trgovine i način povezivanja još treba provjeriti; ne blokira postojeće popravke i pripremu objave.

## Obvezujući cilj (22. 10. 2026.) i kriteriji svake dorade
Korisnik za **cijeli** željeni popis odjednom dobiva najjeftinije odgovarajuće ponude te, ako želi, na jednom mjestu
priprema dostavu svih artikala koje naručuje.
- **Jedan tijek, više narudžbi.** Jedan korisnički tijek može obuhvatiti više zasebnih narudžbi i dostava trgovaca. Jedan
  prijevoz ili jedan ugovor tvrdi se samo ako je stvarno dogovoren.
- **Stanja se razlikuju i ne lažiraju.** Aplikacija razlikuje izračun, pripremljen zahtjev, poslan zahtjev i potvrdu
  trgovca. Sam izračun ili klik nije ugovorena dostava.
- **Ništa se ne šalje bez potvrde.** Zahtjevi, osobni podaci i narudžbe ne šalju se bez korisnikove potvrde konkretnog
  sadržaja i primatelja.

### Firme, izvori i baza ponuda
- **Firme, ne poslovnice.** Uspoređuju se i prikazuju firme, ne pojedinačna prodajna mjesta. Broj izvora ili poslovnica
  nije broj firmi.
- **Isti cjenik jednom po firmi.** Prodajna mjesta s potpuno istim potvrđenim cjenikom (isti artikli i cijene) prikazuju
  se jednom po firmi, a mjesta ostaju kao podrijetlo (`scripts/uvoz.py`, `spoji_firme`).
- **Razlike između poslovnica se ne skrivaju.** Ako se cjenici mjesta razlikuju, ne uzima se proizvoljni minimum. Svaka
  skupina mjesta ostaje zaseban unos s nazivima mjesta i oznakom „cijena vrijedi za …”.
- **Ne spaja se nespojivo.** Različite pravne osobe, proizvodi, specifikacije i pakiranja se ne spajaju.
- **Provjera prije objave:**
  - deduplikacija firmi;
  - jedinstvenost cjenika i iznimke;
  - očuvanje svih valjanih ponuda (provjera u kodu: svaki artikl i cijena svakog mjesta postoji nakon spajanja);
  - podudarnost zbrojeva;
  - mobilni prikaz.
- **Izvori.** Cilj je više od 10 različitih firmi kao početni minimum, bez gornjeg limita. Izvori su provjerljivi i javni,
  s URL-om, datumom cijene i statusom. Ponude se ne izmišljaju i zabrane pristupa se ne zaobilaze. Dodani izvori i
  razlozi neprihvaćanja bilježe se u `docs/izvori.md`.
- **Kriterij usporedbe.** Kriterij je potpuni trošak cijelog istog popisa u cijelim pakiranjima; nepotpune ponude ne
  pobjeđuju kao potpune.
- **Dostava.** Dostava ovisi o provjerenim uvjetima firme ili skladišta i adresi gradilišta. Nepoznata dostava je
  „Dostava na upit”, nikad 0 €.
