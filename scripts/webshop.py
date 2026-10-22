"""
Pilot: cijene sa službenih stranica proizvoda webshopova koji nemaju CSV/XML cjenik: python scripts/webshop.py

Izvor su strukturirani podaci schema.org Product/Offer (JSON-LD) na stranicama proizvoda na službenoj domeni
trgovca. Stranice proizvoda pronalaze se iz sitemapa navedenih u robots.txt (ili uobičajenih putanja). Poštuje se
robots.txt i Crawl-delay; 401/403/JS izazov se ne zaobilaze. Po trgovcu se dnevno pregledava ograničen broj stranica
(kružni red), a ponuda vrijedi CJENIK_VRIJEDI_DANA od provjere.

Provjera ponude: domena stranice = domena trgovca, valuta EUR, cijena > 0, dostupnost, PDV (iz podataka ili teksta
stranice), jedinica i pakiranje iz naziva. Ponuda bez potvrđenog PDV-a ili dostupnosti, ili s rasponom cijena, ostaje
vidljiva, ali se ne rangira. Vrijeme dohvata je "provjereno", nikad datum objave cijene.
"""
import gzip
import json
import re
import sys
import time
import urllib.parse
import urllib.robotparser
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import uvoz  # noqa: E402
from otkrivanje import AGENT, RE_IZAZOV, domena, je_html  # noqa: E402

KORIJEN = Path(__file__).resolve().parent.parent
POPIS = KORIJEN / "scripts" / "webshopovi.json"
IZLAZ = KORIJEN / "site" / "data" / "webshop.json"
PREDMEMORIJA = KORIJEN / ".predmemorija" / "webshop.json"
NAJVISE_STRANICA = 25          # stranica proizvoda po trgovcu po pokretanju
BUDZET_TRGOVCA = 150           # sekundi po trgovcu; ostatak dolazi na red u sljedećem pokretanju (kružni red)
TIMEOUT = 20                   # sekundi po zahtjevu
UKUPNI_BUDZET = 1380           # sekundi za cijeli pilot (posao ima 30 min); preostali trgovci prvi su sljedeći put
NAJMANJI_RAZMAK = 1.0          # sekundi između zahtjeva istom trgovcu (ili Crawl-delay ako je veći)
SITEMAPI = ["/sitemap.xml", "/sitemap_index.xml", "/wp-sitemap.xml", "/product-sitemap.xml"]
RE_PROIZVODNI_SITEMAP = re.compile(r"product|proizvod|artikl|shop|catalog", re.I)
RE_LOC = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.I)
RE_JSONLD = re.compile(r"<script[^>]+application/ld\+json[^>]*>(.*?)</script>", re.I | re.S)
RE_PDV_UKLJUCEN = re.compile(r"(uklju[čc]en\w*\s+pdv|s\s+pdv-?om|sa\s+pdv-?om|pdv\s+(je\s+)?uklju[čc]en|cijena\s+s\s+pdv)", re.I)
DOSTUPNO = ("instock", "limitedavailability", "onlineonly", "instoreonly", "backorder")
NEDOSTUPNO = ("outofstock", "soldout", "discontinued")


def sitemap_lokacije(xml: str) -> tuple[list[str], bool]:
    """(lokacije, je_indeks)."""
    return [urllib.parse.unquote(u) if " " in u else u for u in RE_LOC.findall(xml)], "<sitemapindex" in xml[:2000].lower()


def stranice_proizvoda(korijen: str, dohvati, rp) -> list[str]:
    """URL-ovi stranica proizvoda iz sitemapa: prvo oni iz robots.txt, pa uobičajene putanje dok se ne nađu stranice."""
    korijeni = list(dict.fromkeys(list(rp.site_maps() or []) + [korijen + p for p in SITEMAPI]))
    vidjeni, stranice = set(), []
    for pocetni in korijeni:
        red = [pocetni]
        while red and len(vidjeni) < 12:
            url = red.pop(0)
            if url in vidjeni or not rp.can_fetch(AGENT, url):
                continue
            vidjeni.add(url)
            try:
                sadrzaj = dohvati(url)
                xml = uvoz.dekodiraj(gzip.decompress(sadrzaj) if sadrzaj[:2] == b"\x1f\x8b" else sadrzaj)
            except Exception:  # noqa: BLE001
                continue
            lok, indeks = sitemap_lokacije(xml)
            if indeks:
                proizvodni = [x for x in lok if RE_PROIZVODNI_SITEMAP.search(urllib.parse.urlsplit(x).path)]
                red = (proizvodni or lok) + red
            else:
                stranice += [x for x in lok if domena(x) == domena(korijen)]
        if stranice:
            break
    return list(dict.fromkeys(stranice))


def _cvorovi(podatak):
    if isinstance(podatak, list):
        for x in podatak:
            yield from _cvorovi(x)
    elif isinstance(podatak, dict):
        yield podatak
        for k in ("@graph", "mainEntity", "itemListElement"):
            if k in podatak:
                yield from _cvorovi(podatak[k])


def _tip(cvor) -> set:
    t = cvor.get("@type", [])
    return {str(x).lower() for x in (t if isinstance(t, list) else [t])}


def proizvodi_sa_stranice(html: str) -> list[dict]:
    rezultat = []
    for blok in RE_JSONLD.findall(html):
        try:
            podatak = json.loads(blok.strip())
        except ValueError:
            continue
        rezultat += [c for c in _cvorovi(podatak) if {"product", "productgroup"} & _tip(c)]
    return rezultat


def _tekst(v) -> str:
    if isinstance(v, dict):
        return str(v.get("name") or v.get("@id") or "")
    if isinstance(v, list):
        return _tekst(v[0]) if v else ""
    return str(v or "")


def ponuda_iz_proizvoda(p: dict, url: str, dom: str, html: str, sada: datetime) -> dict:
    """Jedna provjerena ponuda ili zapis s razlogom zašto nije uključena/rangirana."""
    naziv = re.sub(r"\s+", " ", _tekst(p.get("name"))).strip()
    ponude = p.get("offers") or {}
    ponude = ponude if isinstance(ponude, list) else [ponude]
    o = next((x for x in ponude if isinstance(x, dict)), {})
    vrsta = _tip(o)
    spec = o.get("priceSpecification") or {}
    spec = spec[0] if isinstance(spec, list) and spec else spec if isinstance(spec, dict) else {}
    cijena = uvoz.u_broj(o.get("price") if o.get("price") not in (None, "") else spec.get("price"))
    valuta = str(o.get("priceCurrency") or spec.get("priceCurrency") or "").upper()
    dostupnost = _tekst(o.get("availability")).rsplit("/", 1)[-1].lower()
    adresa = _tekst(o.get("url")) or _tekst(p.get("url")) or url
    zapis = {"naziv": naziv, "url": url, "cijena": cijena, "valuta": valuta, "dostupnost": dostupnost or "nepoznata",
             "sku": _tekst(p.get("sku")), "gtin": _tekst(p.get("gtin13") or p.get("gtin") or p.get("gtin14") or p.get("ean")),
             "marka": _tekst(p.get("brand")), "provjereno": sada.isoformat(timespec="minutes")}
    if not naziv:
        return {**zapis, "iskljuceno": "bez naziva"}
    if domena(urllib.parse.urljoin(url, adresa)) != dom:
        return {**zapis, "iskljuceno": "ponuda nije na službenoj domeni"}
    if "aggregateoffer" in vrsta or (cijena is None and o.get("lowPrice")):
        return {**zapis, "cijena": uvoz.u_broj(o.get("lowPrice")), "razlog": "raspon cijena (varijante); nije jedna cijena"}
    if cijena is None or cijena <= 0:
        return {**zapis, "iskljuceno": "bez cijene (npr. cijena na upit)"}
    if valuta != "EUR":
        return {**zapis, "iskljuceno": f"valuta nije EUR ({valuta or 'nije navedena'})"}
    if dostupnost in NEDOSTUPNO:
        return {**zapis, "iskljuceno": "nedostupno"}
    pdv = spec.get("valueAddedTaxIncluded")
    zapis["pdv"] = ("uključen" if str(pdv).lower() == "true" else "nije uključen" if str(pdv).lower() == "false"
                    else "uključen (tekst stranice)" if RE_PDV_UKLJUCEN.search(re.sub(r"<[^>]+>", " ", html)) else "nije naveden")
    razlozi = []
    if zapis["pdv"] == "nije uključen":
        razlozi.append("cijena bez PDV-a")
    elif zapis["pdv"] == "nije naveden":
        razlozi.append("PDV nije naveden")
    if dostupnost not in DOSTUPNO:
        razlozi.append("dostupnost nije navedena")
    return {**zapis, **({"razlog": "; ".join(razlozi)} if razlozi else {})}


def obradi_trgovca(t: dict, dohvati, stanje_reda: dict, sada: datetime, spavaj=time.sleep, sat=time.monotonic) -> tuple[dict, list[dict]]:
    pocetak = sat()
    dom = t["domena"]
    korijen = f"https://{t.get('host') or dom}"
    pregled = {"domena": dom, "naziv": t.get("naziv", dom)}
    rp = urllib.robotparser.RobotFileParser()
    try:
        rp.parse(uvoz.dekodiraj(dohvati(korijen + "/robots.txt")).splitlines())
    except Exception:  # noqa: BLE001 - bez robots.txt nema zabrane
        rp.parse([])
    razmak = max(NAJMANJI_RAZMAK, float(rp.crawl_delay(AGENT) or 0))
    try:
        naslovna = dohvati(korijen + "/")
        if RE_IZAZOV.search(uvoz.dekodiraj(naslovna)[:20000]):
            return {**pregled, "status": "blokiran", "razlog": "zaštita od automatskog pristupa (JS izazov); ne zaobilazi se"}, []
    except Exception as e:  # noqa: BLE001
        return {**pregled, "status": "blokiran", "razlog": f"naslovna nedostupna ({str(e)[:100]})"}, []
    sve = stranice_proizvoda(korijen, dohvati, rp)
    pregled["stranica_u_sitemapu"] = len(sve)
    if not sve:
        return {**pregled, "status": "kandidat", "razlog": "sitemap sa stranicama proizvoda nije pronađen"}, []
    pomak = stanje_reda.get(dom, 0) % len(sve)
    danas = (sve + sve)[pomak:pomak + min(NAJVISE_STRANICA, len(sve))]
    stanje_reda[dom] = pomak  # pomiče se nakon pregleda za stvarno pregledani broj stranica
    ponude, iskljuceno, bez_podataka, odbijeno, pregledano = [], {}, 0, 0, 0
    for url in danas:
        if sat() - pocetak > BUDZET_TRGOVCA:
            break  # ograničenje vremena po trgovcu; red se nastavlja sljedeći put od ove stranice
        pregledano += 1
        if not rp.can_fetch(AGENT, url):
            odbijeno += 1
            continue
        spavaj(razmak)
        try:
            sadrzaj = dohvati(url)
        except Exception:  # noqa: BLE001
            odbijeno += 1
            continue
        html = uvoz.dekodiraj(sadrzaj) if je_html(sadrzaj) or b"ld+json" in sadrzaj[:200000] else ""
        nadjeni = proizvodi_sa_stranice(html)
        if not nadjeni:
            bez_podataka += 1
            continue
        for p in nadjeni[:1]:
            z = ponuda_iz_proizvoda(p, url, dom, html, sada)
            if z.get("iskljuceno"):
                iskljuceno[z["iskljuceno"]] = iskljuceno.get(z["iskljuceno"], 0) + 1
            else:
                ponude.append(z)
    stanje_reda[dom] = (pomak + pregledano) % len(sve)
    pregled.update({"pregledano_stranica": pregledano, "bez_strukturiranih_podataka": bez_podataka, "nedohvatljivo": odbijeno,
                    "ponuda": len(ponude), "rangirljivih": sum(1 for p in ponude if not p.get("razlog")), "iskljuceno": iskljuceno,
                    "primjeri": [{k: p.get(k) for k in ("naziv", "cijena", "pdv", "dostupnost", "razlog", "url")} for p in ponude[:3]]})
    pregled["status"] = "pilot" if ponude else "kandidat"
    if not ponude:
        pregled["razlog"] = "na pregledanim stranicama nema valjane schema.org ponude u EUR"
    return pregled, ponude


def spoji_s_predmemorijom(stare: dict, nove: dict, sada: datetime) -> dict:
    """Ponude po trgovcu i URL-u; novija provjera zamjenjuje stariju, a starije od CJENIK_VRIJEDI_DANA ispadaju."""
    granica = sada - timedelta(days=uvoz.CJENIK_VRIJEDI_DANA)
    rezultat = {}
    for dom in set(stare) | set(nove):
        po_url = {p["url"]: p for p in stare.get(dom, [])}
        po_url.update({p["url"]: p for p in nove.get(dom, [])})
        rezultat[dom] = [p for p in po_url.values() if datetime.fromisoformat(p["provjereno"]) >= granica]
    return rezultat


def main():
    trgovci = json.loads(POPIS.read_text(encoding="utf-8"))["trgovci"]
    sada = datetime.now(timezone.utc)
    try:
        spremljeno = json.loads(PREDMEMORIJA.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        spremljeno = {"red": {}, "ponude": {}}
    dohvati = lambda url: uvoz.preuzmi_url(url, pokusaja=1, timeout=TIMEOUT)  # noqa: E731
    pregledi, nove = [], {}
    nazivi = {t["domena"]: t.get("naziv", t["domena"]) for t in trgovci}
    stare = spremljeno.get("ponude", {})
    pocetak, prvi = time.monotonic(), spremljeno["red"].get("_prvi_trgovac", 0) % max(1, len(trgovci))
    redoslijed = trgovci[prvi:] + trgovci[:prvi]
    for n, t in enumerate(redoslijed):
        if time.monotonic() - pocetak > UKUPNI_BUDZET:
            spremljeno["red"]["_prvi_trgovac"] = (prvi + n) % len(trgovci)
            for ostali in redoslijed[n:]:
                pregledi.append({"domena": ostali["domena"], "status": "nije stigao na red", "razlog": "vrijeme pilota; prvi je sljedeći put"})
                print("-- " + json.dumps(pregledi[-1], ensure_ascii=False), flush=True)
            break
        try:
            pregled, ponude = obradi_trgovca(t, dohvati, spremljeno["red"], sada)
        except Exception as e:  # noqa: BLE001 - jedan trgovac ne ruši pilot
            pregled, ponude = {"domena": t["domena"], "status": "greška", "razlog": str(e)[:200]}, []
        pregledi.append(pregled)
        if ponude:
            nove[t["domena"]] = ponude
        print(("OK " if ponude else "-- ") + json.dumps({k: v for k, v in pregled.items() if k != "primjeri"}, ensure_ascii=False), flush=True)
        for p in pregled.get("primjeri", []):
            print("     " + json.dumps(p, ensure_ascii=False)[:300], flush=True)
        # Spremanje nakon svakog trgovca: prekid (npr. vremensko ograničenje posla) ne gubi već provjerene ponude.
        spremljeno["ponude"] = spoji_s_predmemorijom(stare, nove, sada)
        PREDMEMORIJA.parent.mkdir(parents=True, exist_ok=True)
        PREDMEMORIJA.write_text(json.dumps(spremljeno, ensure_ascii=False), encoding="utf-8")
        IZLAZ.parent.mkdir(parents=True, exist_ok=True)
        IZLAZ.write_text(json.dumps({"provjereno": sada.isoformat(timespec="minutes"), "trgovci": pregledi,
                                     "ponude": {d: {"naziv": nazivi.get(d, d), "ponude": p} for d, p in spremljeno["ponude"].items() if p}},
                                    ensure_ascii=False, indent=1), encoding="utf-8")
    PREDMEMORIJA.parent.mkdir(parents=True, exist_ok=True)
    IZLAZ.parent.mkdir(parents=True, exist_ok=True)
    PREDMEMORIJA.write_text(json.dumps(spremljeno, ensure_ascii=False), encoding="utf-8")  # i pomak reda trgovaca
    IZLAZ.write_text(json.dumps({"provjereno": sada.isoformat(timespec="minutes"), "trgovci": pregledi,
                                 "ponude": {d: {"naziv": nazivi.get(d, d), "ponude": p} for d, p in spremljeno["ponude"].items() if p}},
                                ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Webshop pilot: {sum(1 for p in pregledi if p.get('ponuda'))} trgovaca s ponudama, "
          f"{sum(p.get('ponuda', 0) for p in pregledi)} ponuda danas, "
          f"{sum(p.get('rangirljivih', 0) for p in pregledi)} potpunih za rangiranje")
    return 0


if __name__ == "__main__":
    sys.exit(main())
