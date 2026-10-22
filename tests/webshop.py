"""Pilot cijena sa stranica proizvoda (schema.org), sintetički webshop bez mreže: python3 tests/webshop.py"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import uvoz as u  # noqa: E402
import webshop as w  # noqa: E402

sada = datetime(2026, 10, 21, 9, tzinfo=timezone.utc)


def stranica(proizvod, tekst=""):
    return (f'<!DOCTYPE html><html><head><script type="application/ld+json">{json.dumps(proizvod)}</script></head>'
            f"<body>{tekst}</body></html>").encode()


def proizvod(naziv, cijena="9.90", valuta="EUR", dostupnost="https://schema.org/InStock", pdv=True, **dodatno):
    o = {"@type": "Offer", "price": cijena, "priceCurrency": valuta, "availability": dostupnost}
    if pdv is not None:
        o["priceSpecification"] = {"@type": "PriceSpecification", "price": cijena, "priceCurrency": valuta, "valueAddedTaxIncluded": pdv}
    return {"@context": "https://schema.org", "@type": "Product", "name": naziv, "sku": naziv[:6], "offers": o, **dodatno}


K = "https://shop.hr"
WEB = {
    f"{K}/robots.txt": b"User-agent: *\nDisallow: /zabranjeno/\nSitemap: https://shop.hr/sitemap_index.xml\n",
    f"{K}/": b"<html><title>Shop</title></html>",
    f"{K}/sitemap_index.xml": b'<?xml version="1.0"?><sitemapindex><sitemap><loc>https://shop.hr/post-sitemap.xml</loc></sitemap>'
                              b'<sitemap><loc>https://shop.hr/product-sitemap.xml</loc></sitemap></sitemapindex>',
    f"{K}/product-sitemap.xml": ("<urlset>" + "".join(f"<url><loc>{K}/p/{i}</loc></url>" for i in range(9))
                                 + f"<url><loc>{K}/zabranjeno/x</loc></url><url><loc>https://drugi.hr/p/1</loc></url></urlset>").encode(),
    f"{K}/p/0": stranica(proizvod("Ljepilo za pločice C2TE S1 25 kg", gtin13="3850000000001")),
    f"{K}/p/1": stranica(proizvod("Žbuka strojna 30 kg", cijena="")),                                     # cijena na upit
    f"{K}/p/2": stranica(proizvod("Cement 25 kg", valuta="USD")),
    f"{K}/p/3": stranica(proizvod("Gips 20 kg", dostupnost="https://schema.org/OutOfStock")),
    f"{K}/p/4": stranica({"@type": "Product", "name": "Boja za zidove 15 l",
                          "offers": {"@type": "AggregateOffer", "lowPrice": "20", "highPrice": "40", "priceCurrency": "EUR"}}),
    f"{K}/p/5": stranica(proizvod("Fasadna boja 15 l", pdv=None)),                                        # PDV nije naveden
    f"{K}/p/6": stranica(proizvod("Fuga 5 kg", pdv=None), "Sve cijene su s PDV-om."),                    # PDV iz teksta
    f"{K}/p/7": stranica({"@graph": [{"@type": "WebPage"}, proizvod("Stiropor EPS 100 10 cm 3 m2", pdv=False)]}),
    f"{K}/p/8": stranica(proizvod("Vijak 4x40", url="https://tudji.hr/v")),                              # ponuda tuđe domene
    f"{K}/zabranjeno/x": stranica(proizvod("Ne smije se dohvatiti 1 kg")),
}
dohvaceno = []


def dohvati(url):
    dohvaceno.append(url)
    if url not in WEB:
        raise OSError("HTTP Error 404")
    return WEB[url]


red = {}
pregled, ponude = w.obradi_trgovca({"domena": "shop.hr", "naziv": "Shop"}, dohvati, red, sada, spavaj=lambda s: None)
po = {p["naziv"]: p for p in ponude}
assert pregled["stranica_u_sitemapu"] == 10 and f"{K}/post-sitemap.xml" not in dohvaceno, "product sitemap preferred, other domain dropped"
assert f"{K}/zabranjeno/x" not in dohvaceno and pregled["nedohvatljivo"] == 1, "robots.txt is respected"
assert set(po) == {"Ljepilo za pločice C2TE S1 25 kg", "Boja za zidove 15 l", "Fasadna boja 15 l", "Fuga 5 kg", "Stiropor EPS 100 10 cm 3 m2"}, po
assert "razlog" not in po["Ljepilo za pločice C2TE S1 25 kg"] and po["Ljepilo za pločice C2TE S1 25 kg"]["pdv"] == "uključen"
assert po["Boja za zidove 15 l"]["razlog"].startswith("raspon cijena")
assert po["Fasadna boja 15 l"]["razlog"] == "PDV nije naveden"
assert "razlog" not in po["Fuga 5 kg"] and po["Fuga 5 kg"]["pdv"] == "uključen (tekst stranice)"
assert po["Stiropor EPS 100 10 cm 3 m2"]["razlog"] == "cijena bez PDV-a", "@graph is read; price without VAT is not ranked"
assert pregled["iskljuceno"] == {"bez cijene (npr. cijena na upit)": 1, "valuta nije EUR (USD)": 1, "nedostupno": 1,
                                 "ponuda nije na službenoj domeni": 1}, pregled["iskljuceno"]
assert all(p["provjereno"] == "2026-10-21T09:00+00:00" for p in ponude), "check time recorded, not a publication date"

# JS izazov i nedostupna naslovna: blokirano, bez zaobilaženja.
pb, _ = w.obradi_trgovca({"domena": "b.hr"}, lambda url: b"<title>Just a moment...</title>" if url.endswith("/") else b"",
                         {}, sada, spavaj=lambda s: None)
assert pb["status"] == "blokiran" and "JS izazov" in pb["razlog"], pb

# Kružni red: uz mali limit dva pokretanja pregledaju sve stranice.
stari = w.NAJVISE_STRANICA
w.NAJVISE_STRANICA = 5
red2, vidjeno = {}, set()
for _ in range(2):
    dohvaceno.clear()
    w.obradi_trgovca({"domena": "shop.hr"}, dohvati, red2, sada, spavaj=lambda s: None)
    vidjeno |= {x for x in dohvaceno if "/p/" in x}
assert vidjeno == {f"{K}/p/{i}" for i in range(9)}, vidjeno
w.NAJVISE_STRANICA = stari

# Vremensko ograničenje po trgovcu: stane, a red se nastavlja od prve nepregledane stranice.
vrijeme = iter(range(0, 10000, 40))
red3 = {}
pv, _ = w.obradi_trgovca({"domena": "shop.hr"}, dohvati, red3, sada, spavaj=lambda s: None, sat=lambda: next(vrijeme))
assert 0 < pv["pregledano_stranica"] < 9 and red3["shop.hr"] == pv["pregledano_stranica"], (pv, red3)
# Predmemorija: novija provjera zamjenjuje stariju, starija od dopuštenog ispada.
stara = {"shop.hr": [{**ponude[0], "provjereno": (sada - timedelta(days=5)).isoformat(timespec="minutes"), "url": f"{K}/staro"},
                     {**ponude[0], "provjereno": (sada - timedelta(days=1)).isoformat(timespec="minutes")}]}
spojeno = w.spoji_s_predmemorijom(stara, {"shop.hr": ponude}, sada)["shop.hr"]
assert len(spojeno) == len(ponude) and f"{K}/staro" not in {p["url"] for p in spojeno}

# Uvoz: potpune ponude se rangiraju, nepotpune su vidljive bez rangiranja; nema datuma objave; isti GTIN spaja se s cjenikom.
CJENIK = "Naziv;Barkod;Neto količina;Jedinica mjere;MPC\nLjepilo za pločice C2TE S1 25 kg;3850000000001;25;kg;10,50\n"
izvori = [{"id": "c", "naziv": "Cjenik", "format": "csv", "datum": "2026-10-21"},
          {"id": "web:shop.hr", "naziv": "Shop (web)", "format": "web-json", "url": f"{K}/", "web": True}]
pod, st = u.obradi(izvori, lambda i: CJENIK if i["id"] == "c" else json.dumps(ponude), sada)
web = next(x for x in st if x["id"] == "web:shop.hr")
assert web["uspjeh"] and web["prihvaceno"] == 5 and web["neusporedeno"] == 3 and "datum" not in web, web
assert pod["datumiLanaca"] == ["2026-10-21", ""] and pod["datum"] == "2026-10-21", "web prices do not set the price-list date"
ljepilo = [p for p in pod["proizvodi"] if p[0].startswith("Ljepilo")]
assert len(ljepilo) == 1 and ljepilo[0][5] == [1, 9.9, 0, 10.5], "same GTIN: one product, both stores"
fasadna = next(p for p in pod["proizvodi"] if p[0] == "Fasadna boja 15 l")
assert fasadna[3] == "" and fasadna[7]["razlog"] == "PDV nije naveden" and fasadna[7]["provjereno"] == "2026-10-21"
fuga = next(p for p in pod["proizvodi"] if p[0] == "Fuga 5 kg")
assert fuga[3] == "kg" and fuga[7]["napomena"] == "cijena sa stranice proizvoda · PDV uključen (tekst stranice)"
staro = [{**ponude[0], "provjereno": (sada - timedelta(days=4)).isoformat(timespec="minutes")}]
pz, sz = u.obradi([izvori[1]], lambda i: json.dumps(staro), sada)
assert pz is None and sz[0]["greska"] == "nema dostupnih ponuda" and sz[0]["zastarjelo"] == 1, sz
# Stvarni nalaz (run 33): uspješan web izvor nema datum objave; spremanje predmemorije cjenika ga preskače (bez KeyError).
import tempfile
with tempfile.TemporaryDirectory() as tmp:
    u.spremi_uspjesne(st, {i["id"]: i for i in izvori}, {"c": CJENIK.encode(), "web:shop.hr": b"[]"}, Path(tmp))
    indeks = json.loads((Path(tmp) / "indeks.json").read_text())
    assert list(indeks) == ["c"], indeks
print("WEBSHOP PASS: sitemap index → product pages, robots.txt, other domain, price on request, non-EUR, out of stock, "
      "price range, VAT stated/text/missing/excluded, @graph, JS challenge blocked, rotation, per-shop time budget, cache expiry, "
      "import ranked vs unranked, no publication date, GTIN merge with price list, stale web offers excluded, web source not written to the price-list cache")
