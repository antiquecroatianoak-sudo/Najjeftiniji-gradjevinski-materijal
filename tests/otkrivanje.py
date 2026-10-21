"""Otkrivanje → provjera → uključenje → uvoz, sa sintetičkim webom (bez mreže): python3 tests/otkrivanje.py"""
import importlib.util
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SKRIPTE = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SKRIPTE))
import otkrivanje as o  # noqa: E402
import uvoz as u  # noqa: E402

sada = datetime(2026, 10, 21, 9, tzinfo=timezone.utc)
ZAGLAVLJE = "naziv;šifra;marka;mjerna_jedinica;jedinična_cijena;maloprodajna_cijena;barkod;dostupnost\n"
def csv(n, cijena=5.0):
    return (ZAGLAVLJE + "".join(f'"Cement CEM II/B-M (LL-V) 42,5 N 25 kg tip {i}";"{i}";"X";"KOM";;{cijena + i / 100:.2f};;"dostupan"\n'
                                for i in range(n))).encode()
def xml(datum, n=25):
    return (f'<cjenik generated="{datum}"><proizvodi>' + "".join(
        f"<proizvod><naziv>Ljepilo za pločice C2TE S1 25 kg v{i}</naziv><sifra>{i}</sifra><jedinica_mjere>kom</jedinica_mjere>"
        f"<maloprodajna_cijena>{9 + i / 10:.2f}</maloprodajna_cijena><dostupnost>dostupno</dostupnost></proizvod>" for i in range(n))
        + "</proizvodi></cjenik>").encode()

WEB = {
    # a.hr: naslovna vodi na popis cjenika; dvije poslovnice, za jednu i starija datoteka.
    "https://a.hr/": b'<a href="/o-nama">O nama</a><a href="/cjenik/">Cjenik</a>',
    "https://a.hr/cjenik/": ('<a href="/c/web_Trg_1_A_01_12_21.10.2026_07.00.00.csv">x</a>'
                             '<a href="/c/web_Trg_1_A_01_11_20.10.2026_07.00.00.csv">x</a>'
                             '<a href="/c/poslovnica_Ulica 2_A_02_7_21.10.2026_07.00.00.csv">x</a>').encode(),
    "https://a.hr/c/web_Trg_1_A_01_12_21.10.2026_07.00.00.csv": csv(30),
    "https://a.hr/c/poslovnica_Ulica%202_A_02_7_21.10.2026_07.00.00.csv": csv(25, 6.0),
    # b.hr: nema poveznice, ali postoji uobičajena stalna datoteka s datumom u zaglavlju.
    "https://b.hr/": b"<p>Trgovina</p>",
    "https://b.hr/sidrena-cijena.xml": xml("2026-10-20T23:06:04+00:00"),
    # c.hr: cjenik je zastario.
    "https://c.hr/": b'<a href="https://c.hr/cjenik.xml">XML</a>',
    "https://c.hr/cjenik.xml": xml("2026-10-01T05:00:00+00:00"),
    # f.hr: premalo valjanih ponuda.
    "https://f.hr/sidrena-cijena.xml": xml("2026-10-21T05:00:00+00:00", n=3),
    # e.hr: robots.txt zabranjuje cjenik.
    "https://e.hr/robots.txt": b"User-agent: *\nDisallow: /\n",
    "https://e.hr/cjenik.xml": xml("2026-10-21T05:00:00+00:00"),
}
dohvaceno = []
def dohvati(url):
    dohvaceno.append(url)
    if url.startswith("https://d.hr"):
        raise OSError("HTTP Error 403: Forbidden")
    if url not in WEB:
        raise OSError("HTTP Error 404: Not Found")
    return WEB[url]

# Jedan unos po trgovcu: www. i duplikati se spajaju, ručno uključeni se ne otkrivaju ponovno.
pocetne = o.pocetne_domene([{"naziv": "Ručni", "url": "https://rucni.hr/x.xml", "omogucen": True}],
                           [{"domena": "a.hr"}, {"domena": "www.a.hr"}, {"domena": "b.hr"}, {"domena": "c.hr"},
                            {"domena": "d.hr"}, {"domena": "e.hr"}, {"domena": "f.hr"}, {"domena": "rucni.hr"}])
assert [p["domena"] for p in pocetne] == ["a.hr", "b.hr", "c.hr", "d.hr", "e.hr", "f.hr"], pocetne

smije = o.robots_provjera(dohvati)
rezultati = {}
for t in pocetne:
    nadjeni = o.otkrij(t["pocetna"], dohvati, smije)
    provjere = [o.provjeri(k, dohvati, sada) for k in nadjeni]
    rezultati[t["domena"]] = next((p for p in provjere if p["prihvacen"]), provjere[0] if provjere else None)

assert rezultati["a.hr"]["prihvacen"] and rezultati["a.hr"]["tip"] == "popis" and rezultati["a.hr"]["poslovnica"] == 2
assert rezultati["a.hr"]["datum"] == "2026-10-21" and rezultati["a.hr"]["prihvaceno"] >= 25
assert rezultati["b.hr"]["prihvacen"] and rezultati["b.hr"]["tip"] == "stalni" and rezultati["b.hr"]["datum"] == "2026-10-21"
assert not rezultati["c.hr"]["prihvacen"] and rezultati["c.hr"]["razlog"] == "zastario cjenik od 2026-10-01"
assert rezultati["d.hr"] is None, "403 everywhere: nothing found, no bypass"
assert rezultati["e.hr"] is None and "https://e.hr/cjenik.xml" not in dohvaceno, "robots.txt is respected"
assert not rezultati["f.hr"]["prihvacen"] and rezultati["f.hr"]["razlog"].startswith("premalo valjanih ponuda")

with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    (tmp / "otkriveni.json").write_text(json.dumps({"kandidati": [{**v, "naziv": k} for k, v in rezultati.items() if v]}))
    izvori = o.izvori_iz_otkrivanja(tmp / "otkriveni.json")
    assert [i["naziv"] for i in izvori] == ["a.hr", "b.hr"], "only validated candidates are included"

    def dan(web, mapa):
        def citaj(i):
            if i["url"] not in web:
                raise OSError("HTTP Error 503")
            return web[i["url"]]
        stranica = lambda url: web[url] if url in web else (_ for _ in ()).throw(OSError("HTTP Error 503"))
        razl, ucitaj, preuzeto = u.s_predmemorijom(u.razlozi_izvore(izvori, stranica), citaj, mapa)
        podaci, stanje = u.obradi(razl, ucitaj, sada)
        po_id = {i["id"]: i for i in razl}
        for s in stanje:
            if s["uspjeh"] and s["id"] in preuzeto:
                u.spremi_predmemoriju(mapa, po_id[s["id"]], preuzeto[s["id"]], s["datum"])
        return podaci, stanje

    mapa = tmp / "pm"
    p1, s1 = dan(WEB, mapa)
    assert all(s["uspjeh"] for s in s1) and len(s1) == 3, s1  # 2 poslovnice a.hr + b.hr
    assert len(p1["lanci"]) == 3 and len(p1["proizvodi"]) == 30 + 25 + 25
    # Ponovno pokretanje istog dana: isti rezultat, bez dupliranja.
    p2, _ = dan(WEB, mapa)
    assert len(p2["proizvodi"]) == len(p1["proizvodi"]) and p2["lanci"] == p1["lanci"]
    # Sutra b.hr ne radi: koristi se zadnji valjani cjenik s izvornim datumom, označen.
    bez_b = {k: v for k, v in WEB.items() if not k.startswith("https://b.hr")}
    p3, s3 = dan(bez_b, mapa)
    b = next(s for s in s3 if s["naziv"] == "b.hr")
    assert b["uspjeh"] and b["iz_predmemorije"] and b["datum"] == "2026-10-21"
    assert len(p3["proizvodi"]) == len(p1["proizvodi"])
    # Kad i popis cjenika a.hr padne, koriste se zadnje poznate poslovnice.
    p4, s4 = dan({}, mapa)
    assert all(s["uspjeh"] and s.get("iz_predmemorije") for s in s4) and len(s4) == 3
    # Predmemorija starija od dopuštenog ne rangira se kao aktualna.
    kasnije = datetime(2026, 10, 26, 9, tzinfo=timezone.utc)
    razl, ucitaj, _ = u.s_predmemorijom(u.razlozi_izvore(izvori, lambda url: (_ for _ in ()).throw(OSError("503"))),
                                        lambda i: (_ for _ in ()).throw(OSError("503")), mapa)
    p5, s5 = u.obradi(razl, ucitaj, kasnije)
    assert p5 is None and all(s["greska"].startswith("zastario cjenik od 2026-10-21") for s in s5), s5
    # Atomska objava: neispravan cjenik ne zamjenjuje postojeći.
    izlaz = tmp / "proizvodi.json"
    u.objavi_atomski(p1, izlaz)
    try:
        u.objavi_atomski({**p1, "proizvodi": []}, izlaz)
        raise AssertionError("invalid data must not publish")
    except ValueError:
        pass
    assert len(json.loads(izlaz.read_text())["proizvodi"]) == len(p1["proizvodi"])

# Nove domene iz javnog imenika: samo nepoznate vanjske .hr domene, bez platformi i samog imenika.
def hrana(n):
    return xml("2026-10-21T05:00:00+00:00", n).replace(b"Ljepilo za plo\xc4\x8dice C2TE S1 25 kg", b"Mlijeko 1 l")
IMENIK = {
    "https://imenik.hr/": ('<a href="https://novi.hr/">Novi</a><a href="https://www.novi.hr/x">Novi</a>'
                           '<a href="https://hrana.hr/">Hrana</a><a href="https://a.hr/">poznat</a>'
                           '<a href="https://facebook.com/x">fb</a><a href="https://imenik.hr/o">o</a>'
                           '<a href="https://strani.com/">strani</a><a href="https://isti.hr/">isti</a>').encode(),
    "https://novi.hr/": b"<title>Novi gradjevinski</title>",
    "https://novi.hr/sidrena-cijena.xml": xml("2026-10-21T05:00:00+00:00"),
    "https://hrana.hr/": b"<title>Hrana</title>",
    "https://hrana.hr/sidrena-cijena.xml": hrana(30),
    "https://isti.hr/": b"<title>Novi gradjevinski</title>",
    "https://isti.hr/sidrena-cijena.xml": xml("2026-10-21T05:00:00+00:00"),
}
def dohvati_i(url):
    if url not in IMENIK:
        raise OSError("HTTP Error 404: Not Found")
    return IMENIK[url]
nove = o.domene_iz_imenika("https://imenik.hr/", dohvati_i, {"a.hr"})
assert [n["domena"] for n in nove] == ["novi.hr", "hrana.hr", "isti.hr"], nove
assert all(n["izvor"] == "imenik imenik.hr" for n in nove)
rez = o.dedupliciraj(o.run(nove, dohvati_i, lambda url: True, sada))
po = {r["domena"]: r for r in rez}
assert po["novi.hr"]["prihvacen"] and po["novi.hr"]["udio_gradjevinskog"] == 1.0, po["novi.hr"]
assert not po["hrana.hr"]["prihvacen"] and po["hrana.hr"]["razlog"].startswith("asortiman nije građevinski"), po["hrana.hr"]
assert not po["isti.hr"]["prihvacen"] and po["isti.hr"]["razlog"] == "isti trgovac kao već prihvaćena domena", po["isti.hr"]
# Neobradiva datoteka vraća uzorak za dijagnozu.
pokvaren = o.provjeri({"domena": "p.hr", "tip": "stalni", "url": "https://p.hr/x.xml", "format": "xml"},
                      lambda url: b"<html><body>Prijava</body>", sada)
assert not pokvaren["prihvacen"] and pokvaren.get("uzorak", "").startswith("<html>"), pokvaren
print("DISCOVERY PASS: link + known-path discovery, validation, duplicate supplier, expired, too small, 403, robots.txt, "
      "directory discovery of new domains, construction relevance, same-supplier dedup, parse diagnostics, "
      "inclusion, rerun without duplicates, failed source from last valid list, stale cache excluded, atomic publish")
