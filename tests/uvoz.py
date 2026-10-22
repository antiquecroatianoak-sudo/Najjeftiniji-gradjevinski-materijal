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
# Akcija samo iz oznake cjenika ili niže posebne cijene; bez MPC (samo posebna) nije akcija sama po sebi.
_ak = "Naziv;Šifra;Neto količina;Jedinica mjere;MPC;Posebna cijena;Cijena jedinice\nA 1 kg;1;1;kg;;2,00;2,00\nB 1 kg;2;1;kg;3,00;2,50;2,50\n"
_pa, _sa = u.obradi([{"id": "k", "naziv": "K", "format": "csv", "datum": "2026-10-21"}], lambda i: _ak, datetime(2026, 10, 21, 9, tzinfo=timezone.utc))
_pk = {p[0]: p for p in _pa["proizvodi"]}
assert _pk["A 1 kg"][8][0][2] == 0 and _pk["B 1 kg"][8][0][2] == 1 and _pk["B 1 kg"][8][0][3] == "p", _pk
# Djelomičan komad ("2,5" kom) nije količina: odlučuje naziv; bez količine u nazivu nema poretka.
assert u.mjera("2,5", "kom", 7.5, None, "Ljepilo 2,5 kg") == (2.5, "kg") and u.mjera("0,5", "kom", 3.0, None, "Kist") is None
# Cijena za jedinicu mjere trgovca mora odgovarati cijeni i količini (do zaokruživanja); inače se ponuda ne rangira.
assert u.jedinicna_se_slaze([8.0], 0.32, (25, "kg")) and u.jedinicna_se_slaze([7.99], 0.32, (25, "kg"))
assert u.jedinicna_se_slaze([8.0], 8.0, (25, "kg")), "unit price equal to the price (per pack) is accepted"
assert u.jedinicna_se_slaze([9.0, 8.0], 0.36, (25, "kg")), "regular price matches"
assert not u.jedinicna_se_slaze([8.0], 0.56, (25, "kg")) and u.jedinicna_se_slaze([8.0], None, (25, "kg"))
_cj = "Naziv;Barkod;Neto količina;Jedinica mjere;MPC;Cijena za jedinicu mjere\nCement 25 kg;3850000000017;25;kg;8,00;0,56\nGips 20 kg;3850000000024;20;kg;6,00;0,30\n"
_pod, _st = u.obradi([{"id": "j", "naziv": "J", "format": "csv", "datum": "2026-10-21"}], lambda i: _cj, datetime(2026, 10, 21, 9, tzinfo=timezone.utc))
_po = {p[0]: p for p in _pod["proizvodi"]}
assert _po["Cement 25 kg"][3] == "" and _po["Gips 20 kg"][2:4] == [20, "kg"], _po
assert _st[0]["proturjecna_jedinicna"] == 1 and _st[0]["primjeri_proturjecnih"][0]["jedinicna"] == "0,56", _st[0]

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
assert podaci["lanci"] == ["Trgovina A", "Trgovina B", "Oglasnik 1"], "a source left with only duplicates adds no store"
assert podaci["vrsteIzvora"] == ["trgovina", "trgovina", "oglasnik"]
po_nazivu = {}
for p in podaci["proizvodi"]:
    po_nazivu.setdefault(p[0], []).append(p)
cement = po_nazivu["Cement CEM II/B 25 kg"]
# Trgovina B (XML) navodi cement bez neto količine i bez jedinične cijene: 25 kg piše samo u nazivu, pa ponuda nije
# potvrđena i ne rangira se (zasebna stavka bez količine); trgovina A navodi 25 kg i 0,34 €/kg (potvrđeno).
rang = [p for p in cement if p[3]]
assert len(rang) == 1 and rang[0][5] == [0, 8.5] and rang[0][2:4] == [25, "kg"] and rang[0][6] == "CEM II/B"
assert rang[0][8][0][3] == "p" and rang[0][8][0][0] == 2, "trace: source row 2, quantity confirmed by the unit price"
bez = [p for p in cement if not p[3]]
assert len(bez) == 1 and bez[0][5] == [1, 7.9] and bez[0][8][0][3] == "n", "name-only quantity is not ranked"
assert podaci["urlLanaca"][:2] == ["", ""] and st["b"]["osnova_kolicine"].get("n", 0) >= 1
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
CSV_A = "Naziv;Barkod;Neto količina;Jedinica mjere;MPC\nLaminat hrast 8 mm;3859999000001;2,5;m2;22,50\n"
CSV_B = "Naziv;Barkod;Neto količina;Jedinica mjere;MPC\nLaminat hrast 8 mm;3859999000001;1;kom;4,00\n"
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
<a href="/cjenici/internet-trgovina_Av._Većeslava_Holjevca_42b_Gavroprom_11_20.10.2026_07.40.00.001.csv">CSV</a>
<a href="/cjenici/internet-trgovina_Av._Većeslava_Holjevca_42b_Gavroprom_12_21.10.2026_07.45.09.153.xml">XML</a>
<a href='https://www.primjer.invalid/cjenici/poslovnica_Ilica_1_Gavroprom_3_16.10.2026_07.00.00.csv'>stari</a>
<a href="/o-nama">O nama</a>"""
c = u.cjenici_sa_stranice(HTML, "https://www.primjer.invalid/cjenik")
assert [x["poslovnica"] for x in c] == ["internet-trgovina_Av._Većeslava_Holjevca_42b_Gavroprom", "poslovnica_Ilica_1_Gavroprom"]
assert c[0]["datum"] == "2026-10-21" and c[1]["datum"] == "2026-10-16"
assert c[0]["url"] == ("https://www.primjer.invalid/cjenici/internet-trgovina_Av._Ve%C4%87eslava_Holjevca_42b_"
                       "Gavroprom_12_21.10.2026_07.45.09.153.csv"), c[0]["url"]
c[0]["url"].encode("ascii")
razl = u.razlozi_izvore([{"id": "g", "naziv": "G", "format": "csv", "stranica": "https://www.primjer.invalid/cjenik",
                          "popis": True, "poslovnice": ["internet trgovina"]}], lambda url: HTML.encode())
assert [(x["naziv"], x["datum"]) for x in razl] == [("G · internet-trgovina Av. Većeslava Holjevca 42b Gavroprom", "2026-10-21")], razl
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
# 25 kg piše samo u nazivu (jedinica KOM, bez neto količine i jedinične cijene): vidljivo, bez poretka.
assert cem[2:4] == [0, ""] and cem[5] == [0, 5.56] and cem[6] == "CEM II/B-M (LL-V) · 42,5 N" and cem[8][0][:4] == [3, "484512", 0, "n"], cem
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
assert kljuc10[8] == [[2, "C5110", 1, "c", "Popust"]], "trace keeps row, code, promotion and its name from the list"
assert set(stt[0]["nepoznati_stupci"]) >= {"sidrena_cijena_2026_09_10"} and "poseban_oblik_prodaje" not in stt[0]["nepoznati_stupci"]
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
# Veker: stvarna struktura XML-a od 21.10.2026. (ChatGPT, kosarica #4); stalni naziv datoteke, datum iz "generirano".
VEKER = ('<?xml version="1.0" encoding="UTF-8"?><cjenik vrsta="proizvodi" generirano="2026-10-21T07:30:09+02:00">'
         '<objekt><naziv>Veker.hr</naziv><oblik>Web trgovina</oblik><adresa></adresa><oznaka>01</oznaka><broj_pohrane>34</broj_pohrane>'
         '<vremenska_oznaka>2026-10-21T07:30:09+02:00</vremenska_oznaka></objekt><proizvodi><proizvod><id>7093</id>'
         '<naziv>NEXE Cement 32,5R 25Kg</naziv><sifra>09040001</sifra><marka></marka><jedinica_mjere>kom</jedinica_mjere>'
         '<cijena_za_jedinicu_mjere>5.34</cijena_za_jedinicu_mjere><maloprodajna_cijena>5.34</maloprodajna_cijena>'
         '<redovna_cijena>5.34</redovna_cijena><poseban_oblik_prodaje>ne</poseban_oblik_prodaje><akcijska_cijena></akcijska_cijena>'
         '<referentni_datum>10.09.2026.</referentni_datum><dostupnost>dostupno</dostupnost>'
         '<poveznica>https://www.veker.hr/nexe-cement-325r-25kg/</poveznica></proizvod></proizvodi></cjenik>')
pv, stv = u.obradi([{"id": "v", "naziv": "Veker", "format": "xml", "url": "https://www.veker.hr/wp-content/uploads/cjenici-webshop/cjenik.xml"}],
                   lambda i: VEKER, sada)
assert stv[0]["uspjeh"] and stv[0]["datum"] == "2026-10-21" and stv[0]["prihvaceno"] == 1, stv
nexe = pv["proizvodi"][0]
# Jedinica kom, cijena za jedinicu mjere 5,34 = cijena vreće (nije podatak o osnovi mjere), 25 kg samo u nazivu:
# količina nije potvrđena, ponuda vidljiva bez poretka; trag: zapis 1, šifra 09040001.
assert nexe[0] == "NEXE Cement 32,5R 25Kg" and nexe[2:4] == [0, ""] and nexe[5] == [0, 5.34] and nexe[6] == "32,5 R", nexe
assert nexe[8] == [[1, "09040001", 0, "n"]] and stv[0]["osnova_kolicine"].get("n") == 1, stv
assert pv["urlLanaca"] == ["https://www.veker.hr/wp-content/uploads/cjenici-webshop/cjenik.xml"]
assert pv["datum"] == "2026-10-21"
staro = VEKER.replace('generirano="2026-10-21', 'generirano="2026-10-01').replace("<vremenska_oznaka>2026-10-21", "<vremenska_oznaka>2026-10-01")
assert u.obradi([{"id": "v", "naziv": "Veker", "format": "xml"}], lambda i: staro, sada)[1][0]["greska"] == "zastario cjenik od 2026-10-01"
bez = VEKER.replace(' generirano="2026-10-21T07:30:09+02:00"', '').replace("<vremenska_oznaka>2026-10-21T07:30:09+02:00</vremenska_oznaka>", "")
assert u.obradi([{"id": "v", "naziv": "Veker", "format": "xml"}], lambda i: bez, sada)[1][0]["greska"] == "nepoznat datum cjenika", "referentni_datum is never the price date"
# Neoznačeni href i upit iza nastavka.
cn = u.cjenici_sa_stranice("<a href=/c/web_Trg_1_X_01_5_21.10.2026_07.00.00.csv?v=2>x</a>", "https://x.invalid/")
assert [x["url"] for x in cn] == ["https://x.invalid/c/web_Trg_1_X_01_5_21.10.2026_07.00.00.csv"], cn
# Top Alati: stvarna poveznica s nekodiranim razmacima u navodnicima.
cs = u.cjenici_sa_stranice('<a href="/user-content/cjenici/2026-10-21/prodavaonica_Optujska ulica 169A-42000-Varaždin_P-W1_57_21-10-2026_07-53.csv" class="x">CSV</a>'
                           '<a href="/user-content/cjenici/2026-09-27/prodavaonica_Optujska ulica 169A-42000-Varaždin_P-W1_31_27-09-2026_07-50.csv">CSV</a>',
                           "https://top-alati.hr/prices-list")
assert [(x["datum"], x["url"]) for x in cs] == [("2026-10-21", "https://top-alati.hr/user-content/cjenici/2026-10-21/"
         "prodavaonica_Optujska%20ulica%20169A-42000-Vara%C5%BEdin_P-W1_57_21-10-2026_07-53.csv")], cs
# Datumi iz zaglavlja XML-a: generated (UTC → Zagreb) i datum DD.MM.GGGG.
assert u.datum_objave("2026-10-20T23:06:04+00:00").isoformat() == "2026-10-21", "UTC late evening is next day in Zagreb"
assert u.datum_objave("2026-10-21T01:02:06+00:00").isoformat() == "2026-10-21"
assert u.datum_objave("21.10.2026").isoformat() == "2026-10-21" and u.datum_objave("10.09.2026.").isoformat() == "2026-09-10"
assert u.datum_iz_xml('<cjenik generated="2026-10-20T23:06:04+00:00"><proizvod/></cjenik>').isoformat() == "2026-10-21"
assert u.datum_iz_xml('<cjenik datum="21.10.2026"><proizvod/></cjenik>').isoformat() == "2026-10-21"
# TERMO-METAL Pakrac: datum GGGGMMDD-HHMM u nazivu.
ctm = u.cjenici_sa_stranice('<a href="https://termo-metal.hr/sidrena/cjenik/internet-trgovina_trg-76-bataljuna-7-34550-pakrac_01_28_20261021-0110.xml">x</a>',
                            "https://termo-metal.hr/home/cjenik/", "xml")
assert [x["datum"] for x in ctm] == ["2026-10-21"]
assert ctm[0]["poslovnica"] == "internet-trgovina_trg-76-bataljuna-7-34550-pakrac_01", "storage number 28 is not part of the outlet"
# Sastav cementa i alat (pregled ChatGPT-a na stvarnim datotekama).
assert u.specifikacija("CEMENT 25KG ALPACEM ACEM 2-65 SPECIAL 42,5N CEM II/B-M (LL-V) #64", "kg") == "CEM II/B-M (LL-V) · 42,5 N"
assert u.specifikacija("Cement CEM II/B-S 42,5 N 25 kg", "kg") != u.specifikacija("Cement CEM II/B-M (LL-V) 42,5 N 25 kg", "kg")
assert u.specifikacija("Cement CEM I 52,5 R 25 kg", "kg") == "CEM I · 52,5 R"
assert u.mjera("", "kom", 12.0, None, "Čekić bravarski 500 g") == (1.0, "kom"), "a hammer is priced per piece, never per kg"
assert u.specifikacija("Čekić bravarski 500 g", "kom") != u.specifikacija("Čekić bravarski 800 g", "kom")
assert u.mjera("", "kom", 9.0, None, "Libela aluminijska 60 cm") == (1.0, "kom")
assert u.mjera("", "kg", 9.0, None, "Čekić 500 g") is None, "a tool sold per kg is not comparable"
assert u.mjera("25", "kg", 5.0, None, "Cement 25 kg") == (25, "kg"), "materials are unaffected"
assert u.mjera("", "kom", 5.56, None, "CEMENT 25KG ALPACEM") == (25, "kg")
# Stvarni nalazi probnog pokretanja na GitHubu 21.10.2026.: HTML entiteti i goli "&" u XML-u, poslovnice bez dostupnih ponuda.
X = ('<cjenik generated="2026-10-21T05:00:00+00:00"><proizvod><naziv>Ljepilo&nbsp;C2TE S1 25 kg</naziv><mpc>9,90</mpc>'
     '<jedinica_mjere>kom</jedinica_mjere></proizvod><proizvod><naziv>Vijci & tiple 6 mm</naziv><mpc>2,10</mpc>'
     '<jedinica_mjere>kom</jedinica_mjere></proizvod><proizvod><naziv>Kit &amp; silikon &scaron;</naziv><mpc>4,00</mpc></proizvod></cjenik>')
px, stx = u.obradi([{"id": "x", "naziv": "X", "format": "xml"}], lambda i: X, sada)
assert stx[0]["uspjeh"] and stx[0]["prihvaceno"] == 3, stx
assert sorted(p[0] for p in px["proizvodi"]) == ["Kit & silikon š", "Ljepilo\xa0C2TE S1 25 kg", "Vijci & tiple 6 mm"]
SVE_NEDOSTUPNO = GAVRO.replace('"dostupan"', '"nedostupan"')
p0, st0 = u.obradi([{"id": "z", "naziv": "Z", "format": "csv", "datum": "2026-10-21"},
                    {"id": "g", "naziv": "G", "format": "csv", "datum": "2026-10-21"}],
                   lambda i: SVE_NEDOSTUPNO if i["id"] == "z" else GAVRO, sada)
assert st0[0]["uspjeh"] is False and st0[0]["greska"] == "nema dostupnih ponuda"
assert p0["lanci"] == ["G"] and all(p[5][0] == 0 for p in p0["proizvodi"]), "no empty store, indexes stay consistent"
assert len(p0["datumiLanaca"]) == 1 and len(p2["datumiLanaca"]) == len(p2["lanci"]) and p2["datumiLanaca"][0] == "2026-10-20", \
    "price date per store, aligned with stores"
# Bez izvora nema objave
assert u.obradi([], lambda i: b"", sada)[0] is None

# Brojke: ulazni retci, prihvaćeni retci, spajanje istog proizvoda u istom cjeniku, ponude, jedinstveni proizvodi.
CSV_D = ("Naziv;Barkod;Neto količina;Jedinica mjere;MPC\nLaminat hrast 8 mm;3859999000001;2,5;m2;22,50\n"
         "Laminat hrast 8 mm;3859999000001;2,5;m2;21,90\nCement 25 kg;111;25;kg;6,00\n")
pd_, std = u.obradi([{"id": "a", "naziv": "A", "format": "csv", "datum": "2026-10-20"},
                     {"id": "b", "naziv": "B", "format": "csv", "datum": "2026-10-20"}], lambda i: {"a": CSV_D, "b": CSV_A}[i["id"]], sada)
bd = u.brojke_uvoza(std, pd_)
assert bd == {"ulaznih_redaka": 4, "prihvacenih_redaka": 4, "spojeno_u_izvoru": 1, "ponuda_proizvod_izvor": 3,
              "jedinstvenih_proizvoda": 2}, bd
assert [x["ponuda_u_aplikaciji"] for x in std] == [2, 1] and "lanac" not in std[0]
lam = next(p for p in pd_["proizvodi"] if p[0].startswith("Laminat"))
assert lam[5] == [0, 21.9, 1, 22.5], "the lower of the two rows in the same list, then the other store"
# Mješovita trgovina: uvoze se samo građevinski artikli, ostali se broje (ne nestaju tiho).
MJES = "Naziv;Barkod;Neto količina;Jedinica mjere;MPC\nČokolada 100 g;1;100;g;1,00\nLjepilo za pločice 25 kg;2;25;kg;9,00\n"
pm, sm = u.obradi([{"id": "m", "naziv": "M", "format": "csv", "datum": "2026-10-20", "samo_gradjevinski": True}], lambda i: MJES, sada)
assert [p[0] for p in pm["proizvodi"]] == ["Ljepilo za pločice 25 kg"] and sm[0]["negradjevinsko"] == 1 and sm[0]["primljeno"] == 2
# HTTP 200, ali neispravan sadržaj: zadnji valjani cjenik ostaje, označen, uz današnji kvar; istekli se isključuje.
import tempfile
with tempfile.TemporaryDirectory() as tmp:
    mapa = Path(tmp)
    izv = {"id": "x", "naziv": "X", "format": "xml", "url": "https://x.invalid/c.xml"}
    XML_OK = ('<cjenik generated="2026-10-20T05:00:00+00:00"><proizvod><naziv>Cement 25 kg</naziv><sifra>1</sifra>'
              '<maloprodajna_cijena>6.00</maloprodajna_cijena></proizvod></cjenik>').encode()
    u.spremi_predmemoriju(mapa, izv, XML_OK, "2026-10-20")
    for danas in (b"<!DOCTYPE html><html><body>Odr\xc5\xbeavanje</body></html>", b"<cjenik><proizvod>", b""):
        r, uc, preuzeto = u.s_predmemorijom([dict(izv)], lambda i: danas, mapa)
        pc, sc = u.obradi(r, uc, sada)
        assert sc[0]["uspjeh"] and sc[0]["iz_predmemorije"] and sc[0]["datum"] == "2026-10-20" and sc[0]["danasnja_greska"], sc
        assert [p[0] for p in pc["proizvodi"]] == ["Cement 25 kg"] and pc["datumiLanaca"] == ["2026-10-20"]
        assert "x" in preuzeto, "today's bad content was downloaded, but main() must not cache it (iz_predmemorije)"
    r, uc, _ = u.s_predmemorijom([dict(izv)], lambda i: b"<html></html>", mapa)
    pc, sc = u.obradi(r, uc, datetime(2026, 10, 25, 9, tzinfo=timezone.utc))
    assert pc is None and sc[0]["greska"] == "zastario cjenik od 2026-10-20", sc
    # Popis se otvori, ali bez prepoznatih datoteka: izvor ostaje s razlogom, a zadnje poznate poslovnice ga nadomještaju.
    rod = {"id": "p", "naziv": "P", "format": "xml", "stranica": "https://p.invalid/cjenici/", "popis": True}
    prazno = u.razlozi_izvore([rod], lambda url: b"<html>Cjenici su premje\xc5\xa1teni</html>")
    assert prazno[0]["greska_stranice"] == "na stranici popisa nema prepoznatih cjenika", prazno
    _, sp = u.obradi(prazno, lambda i: b"", sada)
    assert sp[0]["greska"] == "na stranici popisa nema prepoznatih cjenika"
    u.spremi_predmemoriju(mapa, {"id": "p:web", "naziv": "P · web", "format": "xml", "url": "https://p.invalid/a.xml",
                                 "roditelj": "p"}, XML_OK, "2026-10-20")
    r, uc, _ = u.s_predmemorijom(prazno, lambda i: (_ for _ in ()).throw(OSError("nema")), mapa)
    pc, sc = u.obradi(r, uc, sada)
    assert sc[0]["uspjeh"] and sc[0]["iz_predmemorije"] and sc[0]["id"] == "p:web", sc
# Stvarni nalaz (Bačelić, run 31): 36 454 retka s barkodom „0“ spojena su u jedan. „0“ nije barkod; ista šifra spaja,
# isti pravi barkod pod drugom šifrom u istom cjeniku ne spaja (nijanse/veličine).
BAC = ('naziv;šifra;marka;mjerna_jedinica;jedinična_cijena;maloprodajna_cijena;poseban_oblik_prodaje;naziv_posebnog_oblika_prodaje;'
       'sidrena_cijena;sidrena_cijena_od;barkod;dostupnost\n'
       'LJESTVE ŽELJEZNE KUĆNE;1001722;;kom;;30.60;ne;;30.60;2026-09-10;0;dostupan\n'
       'LJESTVE ŽELJEZNE KUĆNE;1001725;;kom;;49.00;ne;;49.00;2026-09-10;0;dostupan\n'
       'JUMIX MARKPro unutrašnja boja 8 KG JU5 010E;5045962;;kom;;14.95;ne;;14.95;2026-09-10;0000000000000;dostupan\n'
       'JUMIX MARKPro unutrašnja boja 8 KG JU5 010F;5045965;;kom;;13.11;ne;;13.11;2026-09-10;0000000000000;dostupan\n'
       'Ljepilo A 25 kg;77;;kom;;9.00;ne;;9.00;2026-09-10;3850000000017;dostupan\n'
       'Ljepilo A 25 kg;78;;kom;;9.50;ne;;9.50;2026-09-10;3850000000017;dostupan\n'
       'Ljepilo A 25 kg;77;;kom;;9.20;ne;;9.20;2026-09-10;3850000000017;dostupan\n')
pb, sb = u.obradi([{"id": "bac", "naziv": "Bačelić", "format": "csv", "datum": "2026-10-21"}], lambda i: BAC, sada)
assert len(pb["proizvodi"]) == 6, [p[0] for p in pb["proizvodi"]]
assert sb[0]["spojeno_u_izvoru"] == 1 and sb[0]["barkod_druga_sifra"] == 1, sb
assert sorted(p[5][1] for p in pb["proizvodi"] if p[0].startswith("LJESTVE")) == [30.6, 49.0], "two ladders stay two offers"
assert u.valjan_barkod("0") == "" and u.valjan_barkod("0000000000000") == "" and u.valjan_barkod("123") == ""
assert u.valjan_barkod(" 3850000000017 ") == "3850000000017" and u.valjan_barkod("40123456") == "40123456"
# Stvarni nalaz (Veker/ARKOR, run 36): ista šifra bez barkoda za različite boje/veličine (Škare PROLINE 31,99/46,99/64,99 €)
# nisu jedan artikl; potpuno isti redak (isti naziv i cijena) se spaja.
VEK = ('<cjenik generated="2026-10-21T05:00:00+00:00">'
       + "".join(f"<proizvod><naziv>{n}</naziv><sifra>{s}</sifra><maloprodajna_cijena>{c}</maloprodajna_cijena></proizvod>"
                 for n, s, c in [("Škare PROLINE za rezanje betonskog željeza", "03020059", "31.99"),
                                 ("Škare PROLINE za rezanje betonskog željeza", "03020059", "46.99"),
                                 ("Pokrivna boja JUBIN DECOR – Crna, 0,65L", "02040008", "10.99"),
                                 ("Pokrivna boja JUBIN DECOR – Crvena, 0,65L", "02040008", "10.99"),
                                 ("Brusna spužva POLAX", "37430021", "1.79"), ("Brusna spužva POLAX", "37430021", "1.79")])
       + "</cjenik>")
pv, sv = u.obradi([{"id": "vek", "naziv": "Veker", "format": "xml"}], lambda i: VEK, sada)
assert len(pv["proizvodi"]) == 5, [p[0] for p in pv["proizvodi"]]
assert sv[0]["spojeno_u_izvoru"] == 1 and sv[0]["zasebne_varijante"] == 2, sv
assert sorted(p[5][1] for p in pv["proizvodi"] if p[0].startswith("Škare")) == [31.99, 46.99]
print("IMPORT PASS: units, dimensions, specs, CSV/XML, merge, special price, classifieds ranking, dedupe, stale, broken source, counts by stage, mixed store, cache after bad 200, empty listing, placeholder barcode 0, same barcode other code, variants under one code")
