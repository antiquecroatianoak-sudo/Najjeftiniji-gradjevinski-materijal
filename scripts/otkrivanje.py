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

# Uobičajene putanje, uključujući one koje generiraju WordPress dodaci za NN 101/2026 (npr. MJDD Sidrena Cijena).
POZNATE_PUTANJE = ["/cjenik/", "/cjenik", "/cjenici/", "/sidrene-cijene/", "/sidrena-cijena/", "/prices-list",
                   "/sidrena-cijena.xml", "/sidrena-cijena.csv", "/sidrena-cijena-001.xml", "/sidrena-cijena-001.csv",
                   "/cjenik.xml"]
RE_POVEZNICA = re.compile(r"""href\s*=\s*(?:"([^"]+)"|'([^']+)'|([^"'\s>]+))""", re.I)
RE_STRANICA_CJENIKA = re.compile(r"cjeni|sidren|prices?-list|price-list", re.I)
RE_TEKST_CJENIKA = re.compile(r"cjeni|sidren|objava cijena|popis cijena|price list", re.I)
RE_DOMENA_U_TEKSTU = re.compile(r"(?<![\w@.-])(?:https?:\\?/\\?/)?(?:www\.)?((?:[a-z0-9-]+\.)+hr)(?![\w-])", re.I)
RE_NIJE_CJENIK = re.compile(r"sitemap|feed|rss|wp-json|oembed", re.I)
# Kandidat mora imati barem toliko valjanih ponuda da bi se smatrao pravim cjenikom.
NAJMANJE_PONUDA = 20
# Novootkriveni trgovac mora prodavati građevinski materijal/opremu: barem ovaj udio naziva s građevinskim pojmom.
NAJMANJI_UDIO_GRADJEVINSKOG = 0.10
GRADJEVINSKI_POJMOVI = re.compile(r"\b(cement|beton|zbuk|malter|mort|ljepil|fug|glet|gips|knauf|rigips|opek|cigl|blok|crijep|"
                                  r"stiropor|eps|xps|vun|izolac|hidroizol|bitum|foli|armatur|profil|osb|iveric|sperploc|letv|"
                                  r"gred|dask|laminat|parket|ploc|boj|lak|lazur|premaz|silikon|kit|pjen|mrez|vijak|vijc|cav|tipl|"
                                  r"cijev|kabel|oluk|mjesalic|busilic|brusilic|kolica|ljestv|skel|lopat|alat|pijes|sljunak|vapn)", re.I)
# Imenici/agregatori i velike platforme nisu trgovci.
NIJE_TRGOVAC = re.compile(r"(facebook|instagram|twitter|x\.com|youtube|linkedin|google|apple|microsoft|wordpress|wikipedia|"
                          r"github|narodne-novine|gov\.hr|zakon\.hr|tiktok|pinterest|whatsapp|viber)", re.I)
# Najviše novih domena iz imenika po pokretanju (ostale dolaze sljedećih dana).
NAJVISE_NOVIH = 80
NAJVISE_STRANICA_IMENIKA = 60


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


def je_html(sadrzaj: bytes) -> bool:
    """Stranica umjesto cjenika (npr. naslovna vraćena za nepostojeću putanju, "soft 404")."""
    pocetak = sadrzaj[:2048].lstrip().lower()
    return pocetak.startswith((b"<!doctype html", b"<html", b"<!--")) and b"<html" in pocetak


def poveznice_cjenika(html: str, osnova: str, dom: str) -> list[str]:
    """Poveznice na istoj domeni ili poddomeni koje vode na cjenik po putanji ili po tekstu poveznice."""
    rezultat = []
    for m in re.finditer(r"<a\b([^>]*)>(.*?)</a>", html, re.I | re.S):
        veze = poveznice(m.group(1), osnova)
        if not veze:
            continue
        url, tekst = veze[0], re.sub(r"<[^>]+>", " ", m.group(2))
        d, put = domena(url), urllib.parse.urlsplit(url).path
        if (d == dom or d.endswith("." + dom)) and (RE_STRANICA_CJENIKA.search(put) or RE_TEKST_CJENIKA.search(tekst)
                                                   or (re.search(r"\.(csv|xml)$", put, re.I) and not RE_NIJE_CJENIK.search(put))):
            rezultat.append(url)
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
        for url in poveznice_cjenika(naslovna, korijen + "/", dom):
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
            d = domena(veza)
            if ((d == dom or d.endswith("." + dom)) and re.search(r"\.(csv|xml)$", urllib.parse.urlsplit(veza).path, re.I)
                    and not RE_NIJE_CJENIK.search(urllib.parse.urlsplit(veza).path)):
                datoteke.append(veza)
    # Uobičajena putanja bez poveznice postaje kandidat samo ako je stvarno dostupna.
    for url in pretpostavljene:
        if url not in datoteke and smije(url):
            try:
                if not je_html(dohvati(url)):
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


def udio_gradjevinskog(proizvodi: list) -> float:
    if not proizvodi:
        return 0.0
    return sum(1 for p in proizvodi if GRADJEVINSKI_POJMOVI.search(uvoz.normaliziraj(p[0]))) / len(proizvodi)


def uzorak(dohvati, url: str) -> str:
    """Početak datoteke koja se ne može obraditi, za dijagnozu (bez osobnih podataka: javni cjenik)."""
    try:
        return re.sub(r"\s+", " ", uvoz.dekodiraj(dohvati(url))[:240])
    except Exception:  # noqa: BLE001
        return ""


def naslov(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    return re.sub(r"\s+", " ", m.group(1)).strip()[:120] if m else ""


def domene_iz_imenika(url: str, dohvati, poznate: set, pregled: dict | None = None) -> list[dict]:
    """
    Nove domene trgovaca iz javnog imenika/agregatora cjenika: vanjske .hr poveznice koje nisu poznate,
    nisu platforme i nisu sam imenik. Provjera da su trgovci građevinskog materijala slijedi u provjeri().
    """
    vlastita = domena(url)
    nove, vidjeno = [], set()
    html = uvoz.dekodiraj(dohvati(url))
    sve = poveznice(html, url)
    if pregled is not None:  # dijagnoza: koliko poveznica i koje vanjske domene imenik ima
        pregled.update({"bajtova": len(html), "poveznica": len(sve),
                        "vanjske": sorted({domena(v) for v in sve if domena(v) != vlastita})[:40]})
    # Imenik često ima zasebnu stranicu po trgovcu: pregledaju se i unutarnje stranice (jedna razina, ograničeno).
    unutarnje = [v for v in dict.fromkeys(sve) if domena(v) == vlastita and v.rstrip("/") != url.rstrip("/")
                 and not re.search(r"\.(css|js|png|jpe?g|svg|webp|ico|pdf|woff2?)(\?|$)", v, re.I)][:NAJVISE_STRANICA_IMENIKA]
    for v in unutarnje:
        try:
            tekst = uvoz.dekodiraj(dohvati(v))
            sve += poveznice(tekst, v) + ["https://" + m.lower() for m in RE_DOMENA_U_TEKSTU.findall(tekst)]
        except Exception:  # noqa: BLE001
            continue
    if pregled is not None:
        pregled["unutarnjih_stranica"] = len(unutarnje)
    # Popis trgovaca često je u tekstu ili ugrađenom JSON-u (prikazuje ga skripta), a ne u poveznicama.
    sve += ["https://" + m.lower() for m in RE_DOMENA_U_TEKSTU.findall(html)]
    for veza in sve:
        d = domena(veza)
        if (not d.endswith(".hr") or d == vlastita or d.endswith("." + vlastita) or d in poznate or d in vidjeno
                or NIJE_TRGOVAC.search(d)):
            continue
        vidjeno.add(d)
        nove.append({"domena": d, "naziv": d, "pocetna": f"https://{d}/", "izvor": f"imenik {vlastita}"})
    return nove


def provjeri(kandidat: dict, dohvati, sada: datetime | None = None, gradjevinski: bool = False) -> dict:
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
        greska = s.get("greska", "nepoznata greška")
        dodatak = {"uzorak": uzorak(dohvati, izvori[0]["url"])} if "well-formed" in greska or "element" in greska or "stupce" in greska else {}
        try:
            if je_html(dohvati(izvori[0]["url"])):
                greska = "na adresi je HTML stranica, ne CSV/XML cjenik"
        except Exception:  # noqa: BLE001
            pass
        return {**kandidat, **dodatak, "prihvacen": False, "razlog": greska}
    s_jedinicom = sum(1 for p in (podaci or {}).get("proizvodi", []) if p[3])
    dokaz = {"datum": s.get("datum"), "primljeno": s.get("primljeno"), "prihvaceno": s.get("prihvaceno"),
             "nedostupno": s.get("nedostupno", 0), "s_jedinicom": s_jedinicom, "provjereno": sada.isoformat(timespec="minutes"),
             "url": s.get("url")}
    if (s.get("prihvaceno") or 0) < NAJMANJE_PONUDA:
        return {**kandidat, **dokaz, "prihvacen": False, "razlog": f"premalo valjanih ponuda ({s.get('prihvaceno')})"}
    dokaz["udio_gradjevinskog"] = round(udio_gradjevinskog(podaci["proizvodi"]), 3)
    if gradjevinski and dokaz["udio_gradjevinskog"] < NAJMANJI_UDIO_GRADJEVINSKOG:
        return {**kandidat, **dokaz, "prihvacen": False, "razlog": f"asortiman nije građevinski ({dokaz['udio_gradjevinskog']:.0%})"}
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


def run(trgovci: list[dict], dohvati, smije, sada: datetime | None = None) -> list[dict]:
    """Za svakog trgovca: otkrij cjenike, provjeri ih i zadrži najbolji. Novi iz imenika moraju biti građevinski."""
    rezultat = []
    for trgovac in trgovci:
        try:
            html = uvoz.dekodiraj(dohvati(f"https://{trgovac['domena']}/")) if smije(f"https://{trgovac['domena']}/") else ""
            trgovac = {**trgovac, "naslov": naslov(html)}
        except Exception:  # noqa: BLE001
            pass
        nadjeni = otkrij(trgovac["pocetna"], dohvati, smije)
        if not nadjeni:
            rezultat.append({**trgovac, "prihvacen": False, "razlog": "cjenik nije pronađen ili je pristup odbijen"})
            continue
        provjere = [provjeri(k, dohvati, sada, gradjevinski=bool(trgovac.get("izvor"))) for k in nadjeni]
        najbolji = next((p for p in provjere if p["prihvacen"]), provjere[0])
        rezultat.append({**trgovac, **najbolji, "ostali": [p for p in provjere if p is not najbolji]})
    return rezultat


def dedupliciraj(rezultat: list[dict]) -> list[dict]:
    """Isti trgovac na dvije domene (isti naslov stranice i isti broj ponuda) prihvaća se jednom."""
    vidjeno = set()
    for r in rezultat:
        if not r.get("prihvacen"):
            continue
        kljuc = (uvoz.normaliziraj(r.get("naslov", "")), r.get("prihvaceno"))
        if kljuc[0] and kljuc in vidjeno:
            r["prihvacen"], r["razlog"] = False, "isti trgovac kao već prihvaćena domena"
        vidjeno.add(kljuc)
    return rezultat


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
    imenici = json.loads(DOMENE.read_text(encoding="utf-8")).get("imenici", []) if DOMENE.exists() else []
    trgovci = pocetne_domene(izvori, dodatne)
    poznate = {t["domena"] for t in trgovci} | {domena(i.get("stranica") or i.get("url") or "") for i in izvori}
    # Nove domene iz javnih imenika cjenika (bez tražilice i bez ključa).
    pregled_imenika = []
    for imenik in imenici:
        try:
            pregled = {}
            nove = domene_iz_imenika(imenik["url"], dohvati, poznate, pregled)[:NAJVISE_NOVIH]
            pregled_imenika.append({"url": imenik["url"], "novih_domena": len(nove), **pregled})
            poznate |= {n["domena"] for n in nove}
            trgovci += nove
        except Exception as e:  # noqa: BLE001
            pregled_imenika.append({"url": imenik["url"], "greska": str(e)[:200]})
    rezultat = run(trgovci, dohvati, smije)
    rezultat = dedupliciraj(rezultat)
    IZLAZ.parent.mkdir(parents=True, exist_ok=True)
    privremeno = IZLAZ.with_suffix(".tmp")
    privremeno.write_text(json.dumps({"azurirano": datetime.now(timezone.utc).isoformat(timespec="minutes"),
                                      "imenici": pregled_imenika, "kandidati": rezultat}, ensure_ascii=False, indent=1), encoding="utf-8")
    privremeno.replace(IZLAZ)
    prihvaceni = [r for r in rezultat if r.get("prihvacen")]
    print(f"Otkrivanje: {len(rezultat)} trgovaca provjereno, {len(prihvaceni)} s valjanim cjenikom")
    for r in rezultat:
        print(("OK " if r.get("prihvacen") else "-- ") + f"{r['domena']}" + (f" [{r['izvor']}]" if r.get("izvor") else "") + ": " + (
            f"{r.get('prihvaceno')} ponuda, cjenik od {r.get('datum')}, {r.get('url') or r.get('stranica')}" if r.get("prihvacen")
            else r.get("razlog", "")) + (f" | uzorak: {r['uzorak'][:160]}" if r.get("uzorak") else ""))
    for i in pregled_imenika:
        print("Imenik: " + json.dumps(i, ensure_ascii=False))
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
