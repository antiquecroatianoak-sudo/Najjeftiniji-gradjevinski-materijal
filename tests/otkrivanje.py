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
    # f.hr: mali izvor (3 ponude) je valjan, uz napomenu za pregled.
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
assert rezultati["f.hr"]["prihvacen"] and rezultati["f.hr"]["napomena"] == "mali izvor (3 ponuda)", rezultati["f.hr"]

with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    (tmp / "otkriveni.json").write_text(json.dumps({"kandidati": [{**v, "naziv": k} for k, v in rezultati.items() if v and k != "f.hr"]}))
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
assert not po["hrana.hr"]["prihvacen"] and po["hrana.hr"]["za_pregled"] and "izdvojen za pregled" in po["hrana.hr"]["razlog"], po["hrana.hr"]
# Isti naslov i broj ponuda nisu dokaz istog trgovca: oba ostaju, drugi je označen za pregled.
assert po["isti.hr"]["prihvacen"] and po["isti.hr"]["moguci_duplikat"] == "novi.hr", po["isti.hr"]
# Potvrđen isti identitet (OIB) na dvije domene: jedan trgovac.
oib = o.dedupliciraj([{"domena": "x.hr", "prihvacen": True, "oib": "1"}, {"domena": "x-shop.hr", "prihvacen": True, "oib": "1"},
                      {"domena": "y.hr", "prihvacen": True, "oib": "2"}])
assert [r["prihvacen"] for r in oib] == [True, False, True] and oib[1]["razlog"] == "isti trgovac (OIB 1) kao x.hr"
# Mješovita trgovina: malo građevinskih artikala (< 10 %) → izvor je valjan, uvoze se samo građevinski artikli.
def mjesovito():
    stavke = [f"Mlijeko 1 l v{i}" for i in range(40)] + ["Ljepilo za pločice C2TE 25 kg", "Cement CEM II 25 kg"]
    return ('<cjenik generated="2026-10-21T05:00:00+00:00">' + "".join(
        f"<proizvod><naziv>{n}</naziv><sifra>{i}</sifra><maloprodajna_cijena>{2 + i / 10:.2f}</maloprodajna_cijena></proizvod>"
        for i, n in enumerate(stavke)) + "</cjenik>").encode()
M = {"https://mjes.hr/": b"<title>Mjes</title>", "https://mjes.hr/sidrena-cijena.xml": mjesovito()}
rm = o.run([{"domena": "mjes.hr", "naziv": "mjes.hr", "pocetna": "https://mjes.hr/", "izvor": "imenik t.hr"}],
           lambda url: M[url] if url in M else (_ for _ in ()).throw(OSError("HTTP Error 404")), lambda url: True, sada)[0]
assert rm["prihvacen"] and rm["samo_gradjevinski"] and rm["gradjevinskih"] == 2 and "mješovita trgovina" in rm["napomena"], rm
with tempfile.TemporaryDirectory() as tmp:
    (Path(tmp) / "o.json").write_text(json.dumps({"kandidati": [rm]}))
    iz = o.izvori_iz_otkrivanja(Path(tmp) / "o.json")
    assert iz[0]["samo_gradjevinski"]
    pm, sm = u.obradi(iz, lambda i: M[i["url"]], sada)
    assert len(pm["proizvodi"]) == 2 and sm[0]["negradjevinsko"] == 40, sm
# Neobradiva datoteka vraća uzorak za dijagnozu.
pokvaren = o.provjeri({"domena": "p.hr", "tip": "stalni", "url": "https://p.hr/x.xml", "format": "xml"},
                      lambda url: b"<html><body>Prijava</body>", sada)
assert not pokvaren["prihvacen"] and pokvaren.get("uzorak", "").startswith("<html>"), pokvaren

# Soft 404: uobičajena putanja vraća naslovnu (HTML) → nije kandidat. Cjenik povezan tekstom poveznice i na poddomeni se nalazi.
NASLOVNA = b'<!DOCTYPE html><html><head><title>G</title></head><body><a href="https://dl.g.hr/export/artikli.xml">Objava cjenika</a></body></html>'
G = {"https://g.hr/": NASLOVNA, "https://g.hr/cjenik.xml": NASLOVNA, "https://g.hr/sidrena-cijena.xml": NASLOVNA,
     "https://dl.g.hr/export/artikli.xml": xml("2026-10-21T05:00:00+00:00")}
def dohvati_g(url):
    if url not in G:
        raise OSError("HTTP Error 404: Not Found")
    return G[url]
kand = o.otkrij("https://g.hr/", dohvati_g)
assert [k["url"] for k in kand] == ["https://dl.g.hr/export/artikli.xml"], kand
assert o.provjeri(kand[0], dohvati_g, sada)["prihvacen"]
html_kandidat = o.provjeri({"domena": "g.hr", "tip": "stalni", "url": "https://g.hr/cjenik.xml", "format": "xml"}, dohvati_g, sada)
assert html_kandidat["razlog"] == "na adresi je HTML stranica, ne CSV/XML cjenik", html_kandidat
# Imenik s unutarnjom stranicom po trgovcu.
IMENIK2 = {"https://im2.hr/": b'<a href="/trgovac/novi">Novi</a><a href="/stil.css">css</a>',
           "https://im2.hr/trgovac/novi": b'<a href="https://novi2.hr/">web</a>'}
pregled = {}
nove2 = o.domene_iz_imenika("https://im2.hr/", lambda url: IMENIK2[url], set(), pregled)
assert [n["domena"] for n in nove2] == ["novi2.hr"] and pregled["unutarnjih_stranica"] == 1, (nove2, pregled)
# Imenik koji trgovce prikazuje skriptom: domene iz teksta/JSON-a, ne iz e-mail adresa.
ugradjeno = b'<script>var t=[{"web":"https:\\/\\/www.json-trg.hr\\/"},{"w":"tekst-trg.hr"}]</script><p>info@mail-trg.hr</p><a href="/x?u=https%3A%2F%2Fkodirano.hr">x</a>'
nove3 = o.domene_iz_imenika("https://im3.hr/", lambda url: ugradjeno, set())
assert [n["domena"] for n in nove3] == ["json-trg.hr", "tekst-trg.hr"], nove3

# Naslovna izravno povezuje jedini datirani CSV, bez stranice cjenika: kandidat ostaje, s datumom iz naziva.
H = {"https://h.hr/": b'<a href="/files/internet-trgovina_Ulica_1_H_01_3_21.10.2026_07.00.00.csv">Cjenik</a>',
     "https://h.hr/files/internet-trgovina_Ulica_1_H_01_3_21.10.2026_07.00.00.csv": csv(22)}
dh = lambda url: H[url] if url in H else (_ for _ in ()).throw(OSError("HTTP Error 404"))
kh = o.otkrij("https://h.hr/", dh)
assert [k["tip"] for k in kh] == ["popis"] and kh[0]["stranica"] == "https://h.hr/", kh
ph = o.provjeri(kh[0], dh, sada)
assert ph["prihvacen"] and ph["datum"] == "2026-10-21" and ph["prihvaceno"] == 22, ph
# XML po sadržaju: proizvodni feed i sitemap nisu odbačeni po nazivu, nego zabilježeni kao nepodržan format s URL-om.
F = {"https://f2.hr/": b'<a href="/feed/products.xml">feed</a><a href="/sitemap.xml">s</a>',
     "https://f2.hr/feed/products.xml": b'<?xml version="1.0"?><rss xmlns:g="http://base.google.com/ns/1.0"><channel><item><g:price>9.90 EUR</g:price></item></channel></rss>',
     "https://f2.hr/sitemap.xml": b'<?xml version="1.0"?><urlset><url><loc>https://f2.hr/</loc></url></urlset>'}
df = lambda url: F[url] if url in F else (_ for _ in ()).throw(OSError("HTTP Error 404"))
kf = o.otkrij("https://f2.hr/", df)
assert sorted(k["url"] for k in kf) == ["https://f2.hr/feed/products.xml", "https://f2.hr/sitemap.xml"], kf
pf = {k["url"]: o.provjeri(k, df, sada) for k in kf}
assert pf["https://f2.hr/feed/products.xml"]["razlog"].startswith("nepodržan format: proizvodni feed"), pf
assert pf["https://f2.hr/feed/products.xml"]["nepodrzano"]["url"] == "https://f2.hr/feed/products.xml"
assert pf["https://f2.hr/sitemap.xml"]["razlog"] == "nepodržan format: sitemap"
# Trajni red: uz male limite, više pokretanja pregleda sve podstranice i sve domene imenika.
stare = (o.NAJVISE_STRANICA_IMENIKA, o.NAJVISE_NOVIH)
o.NAJVISE_STRANICA_IMENIKA, o.NAJVISE_NOVIH = 2, 2
IM = {"https://im4.hr/": "".join(f'<a href="/t/{i}">t</a>' for i in range(5)).encode()}
IM.update({f"https://im4.hr/t/{i}": f'<a href="https://trg{i}.hr/">w</a>'.encode() for i in range(5)})
red = {"imenici": {}, "domene": [], "pomak_domena": 0, "prihvacene": []}
pregledane = set()
for _ in range(6):
    danas, _pr = o.trgovci_iz_imenika_s_redom([{"url": "https://im4.hr/"}], lambda url: IM[url], set(), red)
    pregledane |= {d["domena"] for d in danas}
assert pregledane == {f"trg{i}.hr" for i in range(5)} and len(red["domene"]) == 5, (pregledane, red)
o.azuriraj_red(red, [{"domena": "trg0.hr", "prihvacen": True}])
danas, _pr = o.trgovci_iz_imenika_s_redom([{"url": "https://im4.hr/"}], lambda url: IM[url], set(), red)
assert "trg0.hr" in {d["domena"] for d in danas}, "accepted directory domains are checked every day"
o.NAJVISE_STRANICA_IMENIKA, o.NAJVISE_NOVIH = stare
print("DISCOVERY PASS: link + known-path discovery, validation, duplicate supplier, expired, too small, 403, robots.txt, "
      "directory discovery of new domains, construction relevance, same-supplier dedup, parse diagnostics, soft-404 HTML, link-text and subdomain files, "
      "directory sub-pages, small/mixed stores kept, OIB dedup, homepage dated file, feed by content, rotation queue, "
      "inclusion, rerun without duplicates, failed source from last valid list, stale cache excluded, atomic publish")
