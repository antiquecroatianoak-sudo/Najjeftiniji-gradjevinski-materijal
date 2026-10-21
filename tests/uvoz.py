"""Testovi uvoza (sintetički podaci, nisu stvarne cijene): python3 tests/uvoz.py"""
import importlib.util
from datetime import datetime, timezone
from pathlib import Path

put = Path(__file__).resolve().parent.parent / "scripts" / "uvoz.py"
spec = importlib.util.spec_from_file_location("uvoz", put)
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)

# Brojevi i jedinice
assert u.u_broj("1.234,56") == 1234.56 and u.u_broj("1234.56") == 1234.56 and u.u_broj("12,5 €") == 12.5
assert u.u_broj("") is None and u.u_broj("0") is None and u.u_broj("abc") is None
assert u.mjera("25", "kg", 8.0, None, "Cement") == (25, "kg")
assert u.mjera("1", "kom", 8.0, 0.32, "Ljepilo za pločice C2TE 25 kg") == (25, "kg"), "unit price for kom is not used; name gives 25 kg"
assert u.mjera("", "m2", 22.5, 9.0, "Laminat hrast 8 mm") == (2.5, "m2"), "MPC / cijena za m2 gives pack coverage"
assert u.mjera("2,5 m2", "kom", 22.5, None, "Laminat") == (2.5, "m2")
assert u.mjera("", "kom", 12.0, None, "Pločica 60x60 cm") == (1.0, "kom"), "60x60 cm is a dimension, not 36 m; sold per piece"
assert u.mjera("", "", 12.0, None, "Pločica 60x60 cm") is None
assert u.mjera("", "m", 3.2, None, "PVC cijev 110 mm") == (1.0, "m"), "price per metre; 110 mm is the diameter"
assert u.mjera("", "kom", 30.0, None, "Cement 4x25 kg") == (100, "kg")
assert u.mjera("", "", 5.0, None, "Čekić") is None

# Specifikacija razdvaja neusporedive proizvode
assert u.specifikacija("Stiropor EPS 100 10 cm", "m2") == "EPS 100 · 100 mm"
assert u.specifikacija("Stiropor EPS 100 5 cm", "m2") == "EPS 100 · 50 mm"
assert u.specifikacija("Cement CEM II/B 25 kg", "kg") == "CEM II/B"
assert u.specifikacija("Ljepilo za pločice C2TE S1 25 kg", "kg").startswith("C2TE")
assert u.specifikacija("PVC cijev Ø110 2 m", "kom") == "Ø110"
assert u.specifikacija("Pločica 60x60 cm", "m2") == "60x60cm"
# Neusporedivi razredi i frakcije (pregled #1): svaki par mora dati različite specifikacije.
parovi = [("Cement CEM II/B 32,5 R 25 kg", "Cement CEM II/B 42,5 R 25 kg", "kg"),
          ("Cement CEM II/B 42,5 N 25 kg", "Cement CEM II/B 42,5 R 25 kg", "kg"),
          ("Ljepilo za pločice C2TE S1 25 kg", "Ljepilo za pločice C2TE S2 25 kg", "kg"),
          ("Ljepilo za pločice C1 25 kg", "Ljepilo za pločice C2TE 25 kg", "kg"),
          ("Pijesak 0-4 mm", "Pijesak 4-8 mm", "kg"), ("Šljunak 8/16 mm", "Šljunak 16/32 mm", "kg"),
          ("Pijesak 0-4 mm", "Pijesak", "kg")]
for a1, b1, jed in parovi:
    assert u.specifikacija(a1, jed) != u.specifikacija(b1, jed), (a1, b1, u.specifikacija(a1, jed))
assert u.specifikacija("Cement CEM II/B 32,5 R 25 kg", "kg") == "CEM II/B · 32,5 R"
assert u.specifikacija("Ljepilo za pločice C2TE S1 25 kg", "kg") == "C2TE S1"
assert u.specifikacija("Pijesak 0-4 mm", "kg") == "frakcija 0-4 mm"
assert u.specifikacija("Pijesak 0-4 mm", "m3") == "frakcija 0-4 mm", "grain size is not a thickness"
assert u.specifikacija("Cement 25 kg", "kg") == "", "no spec invented"

CSV = """Naziv proizvoda;Šifra proizvoda;Marka proizvoda;Neto količina;Jedinica mjere;MPC;Cijena za jedinicu mjere;Posebna cijena;Barkod
Cement CEM II/B 25 kg;100;Našicecement;25;kg;8,50;0,34;;3850000000001
Stiropor EPS 100 10 cm;200;;;m2;30,00;10,00;27,00;
Pločica 60x60 cm;300;;;kom;12,00;;;
Neispravan;400;;;kg;0,00;;;
Fugirna masa siva;500;;;;6,00;;;
"""
XML = """<?xml version="1.0" encoding="UTF-8"?>
<cjenik><proizvod><naziv>Cement CEM II/B 25 kg</naziv><sifra>A1</sifra><mpc>7,90</mpc><jedinica_mjere>kom</jedinica_mjere>
<barkod>3850000000001</barkod></proizvod>
<proizvod><naziv>Stiropor EPS 100 5 cm</naziv><mpc>15,00</mpc><jedinica_mjere>m2</jedinica_mjere><cijena_za_jedinicu_mjere>5,00</cijena_za_jedinicu_mjere></proizvod>
</cjenik>"""
sada = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)
OGLASI = [
    {"id": "1", "naziv": "Opeka 25x19x19 nova paleta", "cijena": "450", "valuta": "EUR", "kolicina": "1000", "jedinica": "kom",
     "specifikacija": "25x19x19", "stanje": "novo", "pdv": "nije-obveznik", "lokacija": "Zagreb", "provjereno": "2026-10-19T08:00:00Z",
     "url": "https://primjer.invalid/oglas/1"},
    {"id": "2", "naziv": "Opeka 25x19x19 nova paleta", "cijena": "450", "valuta": "EUR", "kolicina": "1000", "jedinica": "kom",
     "specifikacija": "25x19x19", "stanje": "novo", "pdv": "nije-obveznik", "lokacija": "Zagreb", "provjereno": "2026-10-19T08:00:00Z"},
    {"id": "3", "naziv": "Mješalica za beton", "cijena": "120", "valuta": "EUR", "stanje": "rabljeno", "pdv": "nije-obveznik",
     "provjereno": "2026-10-20T08:00:00Z", "kolicina": "1", "jedinica": "kom"},
    {"id": "4", "naziv": "Skela", "cijenaNaUpit": True, "provjereno": "2026-10-20T08:00:00Z"},
    {"id": "5", "naziv": "Stari oglas", "cijena": "10", "valuta": "EUR", "provjereno": "2026-09-01T08:00:00Z"},
    {"id": "6", "naziv": "Prodano", "cijena": "10", "valuta": "EUR", "prodano": True, "provjereno": "2026-10-20T08:00:00Z"},
]
import json
izvori = [
    {"id": "a", "naziv": "Trgovina A", "vrsta": "trgovina", "format": "csv", "datum": "2026-10-20"},
    {"id": "b", "naziv": "Trgovina B", "vrsta": "trgovina", "format": "xml", "datum": "2026-10-19"},
    {"id": "o1", "naziv": "Oglasnik 1", "vrsta": "oglasnik", "format": "oglasi-json"},
    {"id": "o2", "naziv": "Oglasnik 2", "vrsta": "oglasnik", "format": "oglasi-json"},
    {"id": "pokvaren", "naziv": "Pokvaren", "vrsta": "trgovina", "format": "csv", "datum": "2026-10-20"},
]
sadrzaj = {"a": CSV.encode("cp1250"), "b": XML, "o1": json.dumps(OGLASI[:1] + OGLASI[2:]), "o2": json.dumps(OGLASI[1:2]), "pokvaren": "x;y\n1;2"}
podaci, stanje = u.obradi(izvori, lambda i: sadrzaj[i["id"]], sada)
st = {s["id"]: s for s in stanje}
assert not st["pokvaren"]["uspjeh"] and "naziv i cijena" in st["pokvaren"]["greska"], "a broken source is reported, others continue"
assert st["a"]["prihvaceno"] == 4 and st["a"]["odbaceno"] == 1
assert st["o2"]["duplikata"] == 1, "mirrored listing on a second classifieds site is deduplicated"
assert st["o1"]["zastarjelo"] == 2, "stale and sold listings are removed"
assert podaci["lanci"] == ["Trgovina A", "Trgovina B", "Oglasnik 1", "Oglasnik 2"]
assert podaci["vrsteIzvora"] == ["trgovina", "trgovina", "oglasnik", "oglasnik"]
po_nazivu = {}
for p in podaci["proizvodi"]:
    po_nazivu.setdefault(p[0], []).append(p)
cement = po_nazivu["Cement CEM II/B 25 kg"]
assert len(cement) == 1 and cement[0][5] == [1, 7.9, 0, 8.5], "same barcode merges across stores, cheapest first"
assert cement[0][2:4] == [25, "kg"] and cement[0][6] == "CEM II/B"
eps10 = po_nazivu["Stiropor EPS 100 10 cm"][0]
eps5 = po_nazivu["Stiropor EPS 100 5 cm"][0]
assert eps10[5] == [0, 27.0], "special price is used when lower"
assert eps10[2:4] == [3.0, "m2"] and eps5[2:4] == [3.0, "m2"]
assert eps10[6] != eps5[6], "different thickness is never compared as the same unit"
plocica = po_nazivu["Pločica 60x60 cm"][0]
assert plocica[2:4] == [1.0, "kom"] and plocica[6] == "60x60cm", "tile size separates per-piece comparisons"
assert po_nazivu["Fugirna masa siva"][0][3] == "", "unknown quantity stays visible without unit ranking"
opeka = po_nazivu["Opeka 25x19x19 nova paleta"][0]
assert opeka[2:4] == [1000, "kom"] and opeka[7]["stanje"] == "novo" and "razlog" not in opeka[7]
assert opeka[7]["url"] == "https://primjer.invalid/oglas/1"
mjesalica = po_nazivu["Mješalica za beton"][0]
assert mjesalica[3] == "" and mjesalica[7]["razlog"] == "specifikacija nije navedena", "incomplete ad is unranked with a reason"
assert "Skela" not in po_nazivu, "price on request has no amount"
# Isti barkod, različita jedinica u dva dućana: ne spaja se (inače bi B dobio pogrešnu cijenu po m²).
CSV_A = "Naziv;Barkod;Neto količina;Jedinica mjere;MPC\nLaminat hrast 8 mm;3859999;2,5;m2;22,50\n"
CSV_B = "Naziv;Barkod;Neto količina;Jedinica mjere;MPC\nLaminat hrast 8 mm;3859999;1;kom;4,00\n"
p2, _ = u.obradi([{"id": "a", "naziv": "A", "format": "csv", "datum": "2026-10-20"}, {"id": "b", "naziv": "B", "format": "csv", "datum": "2026-10-20"}],
                 lambda i: {"a": CSV_A, "b": CSV_B}[i["id"]], sada)
redovi = [p for p in p2["proizvodi"] if p[0] == "Laminat hrast 8 mm"]
assert len(redovi) == 2, redovi
assert sorted((p[2], p[3], tuple(p[5])) for p in redovi) == [(1.0, "kom", (1, 4.0)), (2.5, "m2", (0, 22.5))]
# Isti barkod i ista mjera: i dalje se spaja.
p3, _ = u.obradi([{"id": "a", "naziv": "A", "format": "csv", "datum": "2026-10-20"}, {"id": "b", "naziv": "B", "format": "csv", "datum": "2026-10-20"}],
                 lambda i: CSV_A, sada)
assert [p[5] for p in p3["proizvodi"]] == [[0, 22.5, 1, 22.5]]
assert podaci["datum"] == "2026-10-19", "app date is the oldest included price list, not the download time"
# Zastarjeli ili nedatirani cjenik se ne uvozi i javlja se razlog.
p4, st4 = u.obradi([{"id": "s", "naziv": "S", "format": "csv", "datum": "2026-10-06"},
                    {"id": "n", "naziv": "N", "format": "csv"}], lambda i: CSV_A, sada)
assert p4 is None
assert [x["greska"] for x in st4] == ["zastario cjenik od 2026-10-06", "nepoznat datum cjenika"]
# Popis cjenika na stranici: najnoviji CSV po poslovnici, datum iz naziva, Unicode put kodiran.
HTML = """<a href="/cjenici/internet-trgovina_Av._Većeslava_Holjevca_42b_Gavroprom_12_21.10.2026_07.45.09.153.csv">CSV</a>
<a href="/cjenici/internet-trgovina_Av._Većeslava_Holjevca_42b_Gavroprom_12_20.10.2026_07.40.00.001.csv">CSV</a>
<a href="/cjenici/internet-trgovina_Av._Većeslava_Holjevca_42b_Gavroprom_12_21.10.2026_07.45.09.153.xml">XML</a>
<a href='https://www.primjer.invalid/cjenici/poslovnica_Ilica_1_Gavroprom_3_16.10.2026_07.00.00.csv'>stari</a>
<a href="/o-nama">O nama</a>"""
c = u.cjenici_sa_stranice(HTML, "https://www.primjer.invalid/cjenik")
assert [x["poslovnica"] for x in c] == ["internet-trgovina_Av._Većeslava_Holjevca_42b_Gavroprom_12", "poslovnica_Ilica_1_Gavroprom_3"]
assert c[0]["datum"] == "2026-10-21" and c[1]["datum"] == "2026-10-16"
assert c[0]["url"] == ("https://www.primjer.invalid/cjenici/internet-trgovina_Av._Ve%C4%87eslava_Holjevca_42b_"
                       "Gavroprom_12_21.10.2026_07.45.09.153.csv"), c[0]["url"]
c[0]["url"].encode("ascii")
razl = u.razlozi_izvore([{"id": "g", "naziv": "G", "format": "csv", "stranica": "https://www.primjer.invalid/cjenik",
                          "popis": True, "poslovnice": ["internet trgovina"]}], lambda url: HTML.encode())
assert [(x["naziv"], x["datum"]) for x in razl] == [("G · internet-trgovina Av. Većeslava Holjevca 42b Gavroprom 12", "2026-10-21")]
pala = u.razlozi_izvore([{"id": "g", "naziv": "G", "stranica": "https://x.invalid/", "popis": True}],
                        lambda url: (_ for _ in ()).throw(OSError("403")))
_, st5 = u.obradi(pala, lambda i: b"", sada)
assert st5[0]["uspjeh"] is False and "popis cjenika nedostupan" in st5[0]["greska"]
# Stvarni retci iz Gavropromova CSV-a od 21.10.2026. (zaglavlje i retci kako ih je dostavio ChatGPT na kosarica #4).
GAVRO = ('naziv;šifra;marka;mjerna_jedinica;jedinična_cijena;maloprodajna_cijena;poseban_oblik_prodaje;'
         'naziv_posebnog_oblika_prodaje;sidrena_cijena;sidrena_cijena_od;barkod;dostupnost\n'
         '"TERANIL EKSTRA GLET MASA, SAMOBORKA 25/1 (48#)";"00007";"SAMOBORKA";"KOM";;12.74;"ne";;12.74;2026-09-10;;"dostupan"\n'
         '"CEMENT 25KG ALPACEM ACEM 2-65 SPECIAL 42,5N CEM II/B-M (LL-V) #64";"484512";"ALPACEM";"KOM";;5.56;"ne";;5.56;2026-09-10;;"dostupan"\n'
         '"STIROPOR EPS GRAFITNI 12CM BEZ PREKLOPA";"00071";"OSTALO";"M2";;15.87;"ne";;15.87;2026-09-10;;"nedostupan"\n')
pg, stg = u.obradi([{"id": "g", "naziv": "Gavroprom", "format": "csv", "datum": "2026-10-21"}], lambda i: GAVRO, sada)
po = {p[0]: p for p in pg["proizvodi"]}
glet = po["TERANIL EKSTRA GLET MASA, SAMOBORKA 25/1 (48#)"]
assert glet[2:4] == [0, ""] and glet[5] == [0, 12.74], "25/1 alone is not a verified 25 kg: listed, unranked"
cem = po["CEMENT 25KG ALPACEM ACEM 2-65 SPECIAL 42,5N CEM II/B-M (LL-V) #64"]
assert cem[2:4] == [25, "kg"] and cem[5] == [0, 5.56] and cem[6] == "CEM II/B · 42,5 N", cem
assert "STIROPOR EPS GRAFITNI 12CM BEZ PREKLOPA" not in po, "unavailable rows are not offered"
assert stg[0]["nedostupno"] == 1 and stg[0]["prihvaceno"] == 2
assert pg["datum"] == "2026-10-21", "date from the file listing, not sidrena_cijena_od"
assert u.specifikacija("STIROPOR EPS GRAFITNI 12CM BEZ PREKLOPA", "m2") == "grafitni · 120 mm"
# Top Alati, stvarno zaglavlje i redak 21.10.2026. (ChatGPT, kosarica #4); dostupnost "nedostupno" se ne uvozi.
TOP = ('naziv;sifra;marka;jedinica_mjere;cijena_jedinice_mjere;maloprodajna_cijena;poseban_oblik_prodaje;'
       'naziv_posebnog_oblika_prodaje;sidrena_cijena_2026_09_10;barkod;raspolozivost\n'
       '"Produženi nasadni ključ, 10 mm";"C5110";"Richmann";"KOM";;"2,17";"Da";"Popust";"2,84";"";"dostupno"\n'
       '"Produženi nasadni ključ, 12 mm";"C5112";"Richmann";"KOM";;"2,40";"ne";;"2,40";"";"nedostupno"\n')
pt, stt = u.obradi([{"id": "t", "naziv": "Top Alati", "format": "csv", "datum": "2026-10-21"}], lambda i: TOP, sada)
assert stt[0]["prihvaceno"] == 1 and stt[0]["nedostupno"] == 1
kljuc10 = pt["proizvodi"][0]
assert kljuc10[0] == "Produženi nasadni ključ, 10 mm" and kljuc10[5] == [0, 2.17] and kljuc10[2:4] == [1.0, "kom"] and kljuc10[6] == "10 mm"
# Nazivi datoteka Top Alata i Vekera.
HTML2 = ("<a href=\"https://top-alati.hr/user-content/cjenici/2026-10-21/prodavaonica_Optujska%20ulica%20169A-42000-"
         "Vara%C5%BEdin_P-W1_57_21-10-2026_07-53.csv\">x</a>"
         "<a href=\"https://top-alati.hr/user-content/cjenici/2026-10-20/prodavaonica_Optujska%20ulica%20169A-42000-"
         "Vara%C5%BEdin_P-W1_57_20-10-2026_07-50.csv\">x</a>"
         "<a href=\"/wp-content/uploads/cjenici-webshop/cjenik_20261020T073012.xml\">x</a>"
         "<a href=\"/wp-content/uploads/cjenici-webshop/cjenik.xml\">x</a>")
ct = u.cjenici_sa_stranice(HTML2, "https://top-alati.hr/prices-list")
assert [(x["datum"], x["url"].endswith("21-10-2026_07-53.csv")) for x in ct] == [("2026-10-21", True)], ct
assert "%20" in ct[0]["url"] and "%C5%BE" in ct[0]["url"], ct[0]["url"]
cv = u.cjenici_sa_stranice(HTML2, "https://www.veker.hr/cjenici/", "xml")
assert [x["datum"] for x in cv] == ["2026-10-20"], "undated cjenik.xml is ignored; dated archive file is used"
# Bez izvora nema objave
assert u.obradi([], lambda i: b"", sada)[0] is None
print("IMPORT PASS: units, dimensions, specs, CSV/XML, merge, special price, classifieds ranking, dedupe, stale, broken source")
