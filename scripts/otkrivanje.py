"""
Otkrivanje javnih cjenika građevinskih trgovaca.

Polazi od službenih domena trgovaca (scripts/izvori.json i scripts/domene.json) i na svakoj traži
stranice s cjenicima (NN 101/2026) i same datoteke: poveznice s naslovne stranice i uobičajene
putanje (/cjenik/, /sidrene-cijene/, /sidrena-cijena.xml ...). Svaki pronađeni cjenik preuzme se i
provjeri istim uvozom kao i glavni cjenik: datum objave, broj valjanih cijena, jedinice.

Rezultat je site/data/otkriveni.json: svi kandidati s dokazom ili razlogom odbijanja. Kandidati koji
prođu provjeru ulaze u dnevni uvoz (scripts/uvoz.py --otkriveni). Ne zaobilaze se blokade (403,
robots.txt) i ne koristi se plaćena tražilica: nove domene dodaje čovjek u scripts/domene.json.

Pokretanje:  python scripts/otkrivanje.py
"""

import json
import re
import sys
import urllib.parse
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import uvoz  # noqa: E402

KORIJEN = Path(__file__).resolve().parent.parent
DOMENE = KORIJEN / "scripts" / "domene.json"
IZLAZ = KORIJEN / "site" / "data" / "otkriveni.json"
AGENT = "najjeftiniji-gradjevinski-materijal/1 (javni cjenik)"

POZNATE_PUTANJE = ["/cjenik/", "/cjenik", "/cjenici/", "/sidrene-cijene/", "/sidrena-cijena/", "/prices-list",
                   "/sidrena-cijena.xml", "/cjenik.xml"]
RE_POVEZNICA = re.compile(r"""href\s*=\s*(?:"([^"]+)"|'([^']+)'|([^"'\s>]+))""", re.I)
RE_STRANICA_CJENIKA = re.compile(r"cjeni|sidren|prices?-list|price-list", re.I)
# Kandidat mora imati barem toliko valjanih ponuda da bi se smatrao pravim cjenikom.
NAJMANJE_PONUDA = 20


def domena(url: str) -> str:
    """Trgovac = domena bez "www." (poslovnice i poddomene istog trgovca nisu različiti trgovci)."""
    host = urllib.parse.urlsplit(url if "//" in url else "https://" + url).hostname or ""
    return host.lower().removeprefix("www.")


def poveznice(html: str, osnova: str) -> list[str]:
    rezultat = []
    for g in RE_POVEZNICA.findall(html):
        href = next(x for x in g if x) if any(g) else ""
        if href and not href.startswith(("mailto:", "tel:", "javascript:", "#")):
            rezultat.append(urllib.parse.urljoin(osnova, href.strip()))
    return rezultat


def otkrij(pocetna: str, dohvati, robots=None) -> list[dict]:
    """
    Cjenici na službenoj domeni: stranice s popisom datoteka ("popis") i stalne datoteke ("stalni").
    dohvati(url) -> bytes ili iznimka. robots(url) -> smije li se dohvatiti.
    """
    dom = domena(pocetna)
    smije = robots or (lambda url: True)
    korijen = f"https://{urllib.parse.urlsplit(pocetna if '//' in pocetna else 'https://' + pocetna).hostname}"
    stranice, datoteke, pretpostavljene = [], [], []
    try:
        if not smije(korijen + "/"):
            raise PermissionError("robots.txt")
        naslovna = uvoz.dekodiraj(dohvati(korijen + "/"))
        for url in poveznice(naslovna, korijen + "/"):
            if domena(url) == dom and RE_STRANICA_CJENIKA.search(urllib.parse.urlsplit(url).path):
                (datoteke if re.search(r"\.(csv|xml)$", urllib.parse.urlsplit(url).path, re.I) else stranice).append(url)
    except Exception:  # noqa: BLE001 - naslovna nedostupna: probaj uobičajene putanje
        pass
    for put in POZNATE_PUTANJE:
        url = korijen + put
        (pretpostavljene if put.endswith((".xml", ".csv")) else stranice).append(url)
    kandidati, vidjeno = [], set()
    for url in dict.fromkeys(stranice):
        if not smije(url):
            continue
        try:
            html = uvoz.dekodiraj(dohvati(url))
        except Exception:  # noqa: BLE001
            continue
        for oblik in ("csv", "xml"):
            datirani = uvoz.cjenici_sa_stranice(html, url, oblik)
            if datirani:
                kljuc = (url, oblik)
                if kljuc not in vidjeno:
                    vidjeno.add(kljuc)
                    kandidati.append({"domena": dom, "tip": "popis", "stranica": url, "format": oblik,
                                      "primjer": datirani[0]["url"], "poslovnica": len(datirani)})
        for veza in poveznice(html, url):
            if domena(veza) == dom and re.search(r"\.(csv|xml)$", urllib.parse.urlsplit(veza).path, re.I):
                datoteke.append(veza)
    # Uobičajena putanja bez poveznice postaje kandidat samo ako je stvarno dostupna.
    for url in pretpostavljene:
        if url not in datoteke and smije(url):
            try:
                dohvati(url)
                datoteke.append(url)
            except Exception:  # noqa: BLE001
                pass
    for url in dict.fromkeys(datoteke):
        ime = urllib.parse.unquote(urllib.parse.urlsplit(url).path.rsplit("/", 1)[-1])
        if uvoz.RE_DATUM_DATOTEKE.search(ime) or uvoz.RE_DATUM_KOMPAKTNO.search(ime):
            continue  # datirane datoteke pokriva kandidat "popis"
        if smije(url) and url not in vidjeno:
            vidjeno.add(url)
            kandidati.append({"domena": dom, "tip": "stalni", "url": url,
                              "format": "xml" if url.lower().endswith(".xml") else "csv"})
    return kandidati


def provjeri(kandidat: dict, dohvati, sada: datetime | None = None) -> dict:
    """Preuzme i uveze kandidat istim uvozom kao glavni cjenik. Vraća dokaz ili razlog odbijanja."""
    sada = sada or datetime.now(timezone.utc)
    izvor = {"id": f"otkriveno:{kandidat['domena']}", "naziv": kandidat["domena"], "vrsta": "trgovina",
             "format": kandidat["format"]}
    try:
        if kandidat["tip"] == "popis":
            izvori = uvoz.razlozi_izvore([{**izvor, "stranica": kandidat["stranica"], "popis": True}], dohvati)[:1]
        else:
            izvori = [{**izvor, "url": kandidat["url"]}]
        if not izvori:
            return {**kandidat, "prihvacen": False, "razlog": "na stranici nema datiranih datoteka"}
        podaci, stanje = uvoz.obradi(izvori, lambda i: dohvati(i["url"]), sada)
    except Exception as e:  # noqa: BLE001
        return {**kandidat, "prihvacen": False, "razlog": f"dohvat ili obrada nije uspjela: {e}"[:300]}
    s = stanje[0] if stanje else {}
    if not s.get("uspjeh"):
        return {**kandidat, "prihvacen": False, "razlog": s.get("greska", "nepoznata greška")}
    s_jedinicom = sum(1 for p in (podaci or {}).get("proizvodi", []) if p[3])
    dokaz = {"datum": s.get("datum"), "primljeno": s.get("primljeno"), "prihvaceno": s.get("prihvaceno"),
             "nedostupno": s.get("nedostupno", 0), "s_jedinicom": s_jedinicom, "provjereno": sada.isoformat(timespec="minutes"),
             "url": s.get("url")}
    if (s.get("prihvaceno") or 0) < NAJMANJE_PONUDA:
        return {**kandidat, **dokaz, "prihvacen": False, "razlog": f"premalo valjanih ponuda ({s.get('prihvaceno')})"}
    return {**kandidat, **dokaz, "prihvacen": True, "razlog": ""}


def pocetne_domene(izvori: list[dict], dodatne: list[dict]) -> list[dict]:
    """Jedan unos po trgovcu (domeni); ručno uključeni izvori se ne otkrivaju ponovno."""
    rucni = {domena(i.get("stranica") or i.get("url") or "") for i in izvori if i.get("omogucen")}
    vidjeno, rezultat = set(), []
    for i in [*izvori, *dodatne]:
        adresa = i.get("stranica") or i.get("url") or i.get("domena")
        if not adresa:
            continue
        d = domena(adresa)
        if d and d not in vidjeno and d not in rucni:
            vidjeno.add(d)
            rezultat.append({"domena": d, "naziv": i.get("naziv", d), "pocetna": adresa})
    return rezultat


def robots_provjera(dohvati):
    predmemorija = {}

    def smije(url: str) -> bool:
        dijelovi = urllib.parse.urlsplit(url)
        korijen = f"{dijelovi.scheme}://{dijelovi.netloc}"
        if korijen not in predmemorija:
            rp = urllib.robotparser.RobotFileParser()
            try:
                rp.parse(uvoz.dekodiraj(dohvati(korijen + "/robots.txt")).splitlines())
            except Exception:  # noqa: BLE001 - bez robots.txt nema zabrane
                rp.parse([])
            predmemorija[korijen] = rp
        return predmemorija[korijen].can_fetch(AGENT, url)
    return smije


def main():
    izvori = json.loads(uvoz.IZVORI.read_text(encoding="utf-8"))["izvori"]
    dodatne = json.loads(DOMENE.read_text(encoding="utf-8"))["domene"] if DOMENE.exists() else []
    zapamceno = {}

    def dohvati(url):  # isti URL u jednom pokretanju preuzima se jednom
        if url not in zapamceno:
            try:
                zapamceno[url] = uvoz.preuzmi_url(url, pokusaja=2, cekanje=1.0)
            except Exception as e:  # noqa: BLE001
                zapamceno[url] = e
        if isinstance(zapamceno[url], Exception):
            raise zapamceno[url]
        return zapamceno[url]
    smije = robots_provjera(dohvati)
    rezultat = []
    for trgovac in pocetne_domene(izvori, dodatne):
        nadjeni = otkrij(trgovac["pocetna"], dohvati, smije)
        if not nadjeni:
            rezultat.append({**trgovac, "prihvacen": False, "razlog": "cjenik nije pronađen ili je pristup odbijen"})
            continue
        provjere = [provjeri(k, dohvati) for k in nadjeni]
        najbolji = next((p for p in provjere if p["prihvacen"]), provjere[0])
        rezultat.append({**trgovac, **najbolji, "ostali": [p for p in provjere if p is not najbolji]})
    IZLAZ.parent.mkdir(parents=True, exist_ok=True)
    privremeno = IZLAZ.with_suffix(".tmp")
    privremeno.write_text(json.dumps({"azurirano": datetime.now(timezone.utc).isoformat(timespec="minutes"),
                                      "kandidati": rezultat}, ensure_ascii=False, indent=1), encoding="utf-8")
    privremeno.replace(IZLAZ)
    prihvaceni = [r for r in rezultat if r.get("prihvacen")]
    print(f"Otkrivanje: {len(rezultat)} trgovaca provjereno, {len(prihvaceni)} s valjanim cjenikom")
    for r in rezultat:
        print(("OK " if r.get("prihvacen") else "-- ") + f"{r['domena']}: " + (
            f"{r.get('prihvaceno')} ponuda, cjenik od {r.get('datum')}" if r.get("prihvacen") else r.get("razlog", "")))
    return 0


def izvori_iz_otkrivanja(put: Path) -> list[dict]:
    """Prihvaćeni kandidati kao izvori za uvoz (jedan po trgovcu)."""
    if not put.exists():
        return []
    izvori = []
    for k in json.loads(put.read_text(encoding="utf-8")).get("kandidati", []):
        if not k.get("prihvacen"):
            continue
        izvor = {"id": f"otkriveno:{k['domena']}", "naziv": k.get("naziv") or k["domena"], "vrsta": "trgovina",
                 "format": k["format"], "status": "provjereno", "omogucen": True, "otkriveno": True}
        izvor.update({"stranica": k["stranica"], "popis": True} if k["tip"] == "popis" else {"url": k["url"]})
        izvori.append(izvor)
    return izvori


if __name__ == "__main__":
    sys.exit(main())
