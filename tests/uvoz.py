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
assert u.specifikacija("Pijesak 0-4 mm", "kg") == "", "kg goods have no thickness spec"

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
# Bez izvora nema objave
assert u.obradi([], lambda i: b"", sada)[0] is None
print("IMPORT PASS: units, dimensions, specs, CSV/XML, merge, special price, classifieds ranking, dedupe, stale, broken source")
