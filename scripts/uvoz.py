"""
Uvoz cijena građevinskog materijala i opreme.

Izvori su popisani u scripts/izvori.json. Uvoze se samo izvori koji su ručno
provjereni ("status": "provjereno") i uključeni ("omogucen": true). Ništa se ne
izmišlja: ako nijedan izvor ne da podatke, aplikacija se ne objavljuje s praznim
ili lažnim cjenikom.

Formati:
  - "csv" / "xml": javni cjenici trgovaca na malo (NN 101/2026, NN 110/2026).
    Struktura nije propisana, pa se stupci prepoznaju po uobičajenim nazivima
    (naziv, šifra, marka, MPC, jedinica mjere, cijena za jedinicu mjere...),
    a izvor može zadati vlastite nazive stupaca ("stupci").
  - "oglasi-json": ponude iz oglasnika u zajedničkom obliku (vidi docs/izvori.md).
    Oglas se rangira samo ako su poznati cijena u EUR, količina i jedinica,
    specifikacija i stanje; ostali su vidljivi kao neuspoređeni.

Rezultat: site/data/proizvodi.json (isti oblik kao u aplikaciji za namirnice,
verzija 2, uz specifikaciju i podatke o ponudi) i site/data/stanje-izvora.json.

Pokretanje:  python scripts/uvoz.py [--izvori put/izvori.json] [--lokalno datoteka ...]
"""

import argparse
import csv
import html.entities
import io
import json
import math
import os
import time
import re
import sys
import unicodedata
import urllib.parse
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from pathlib import Path

KORIJEN = Path(__file__).resolve().parent.parent
IZVORI = KORIJEN / "scripts" / "izvori.json"
IZLAZ = KORIJEN / "site" / "data" / "proizvodi.json"
STANJE = KORIJEN / "site" / "data" / "stanje-izvora.json"
# Zadnji valjani cjenik svakog izvora (ne objavljuje se; u GitHub Actions čuva se predmemorijom).
PREDMEMORIJA = KORIJEN / ".predmemorija"
# Oglas stariji od ovoga smatra se zastarjelim i ne prikazuje se.
OGLAS_VRIJEDI_DANA = 7
# Cjenik trgovca stariji od ovoga ne ulazi u usporedbu (obveza je dnevna objava, NN 101/2026).
CJENIK_VRIJEDI_DANA = 3

# Pojmovi građevinskog asortimana. Služe samo za odvajanje artikala mješovite trgovine, ne za odbacivanje izvora.
GRADJEVINSKI_POJMOVI = re.compile(r"\b(cement|beton|zbuk|malter|mort|ljepil|fug|glet|gips|knauf|rigips|opek|cigl|blok|crijep|"
                                  r"stiropor|eps|xps|vun|izolac|hidroizol|bitumen|folij|armatur|mrez|profil|osb|iveric|sper|"
                                  r"letv|gred|dask|laminat|parket|ploc|boj|lak|lazur|premaz|silikon|kit|pjen|vijak|vijc|cavl|"
                                  r"tipl|cijev|kabel|oluk|zlijeb|mjesalic|busilic|brusilic|kolic|ljestv|skel|lopat|zlic|"
                                  r"gleteric|alat|pijes|sljun|tucan|vapn|kamen|drv|oplat|grijanj|radijator|sanitar|slavin|"
                                  r"kupaon|pvc|ppr|bakren|fasad|krov|prozor|vrat)", re.I)


def je_gradjevinski(naziv: str) -> bool:
    return bool(GRADJEVINSKI_POJMOVI.search(normaliziraj(naziv)))


# Jedinica -> (osnovna jedinica, faktor).
JEDINICE = {
    "mg": ("kg", 1e-6), "g": ("kg", 0.001), "gr": ("kg", 0.001), "dag": ("kg", 0.01),
    "kg": ("kg", 1), "t": ("kg", 1000), "tona": ("kg", 1000),
    "ml": ("l", 0.001), "cl": ("l", 0.01), "dl": ("l", 0.1), "l": ("l", 1), "lit": ("l", 1), "litra": ("l", 1),
    "mm": ("m", 0.001), "cm": ("m", 0.01), "m": ("m", 1), "dm": ("m", 0.1), "met": ("m", 1), "metar": ("m", 1),
    "m2": ("m2", 1), "m²": ("m2", 1), "m^2": ("m2", 1), "qm": ("m2", 1),
    "m3": ("m3", 1), "m³": ("m3", 1), "m^3": ("m3", 1),
    "kom": ("kom", 1), "komad": ("kom", 1), "kos": ("kom", 1), "par": ("kom", 1),
}
# Granice prepoznavanja količine (ne cijene): izvan njih količina je nepoznata, ponuda ostaje vidljiva.
NAJVISE = {"kg": 2000, "l": 1000, "m": 1000, "m2": 500, "m3": 50, "kom": 10000}

STUPCI = {
    "naziv": ["naziv", "naziv proizvoda", "naziv artikla", "proizvod", "artikl", "name"],
    "sifra": ["sifra", "sifra proizvoda", "sifra artikla", "kod", "kod proizvoda", "product id", "id"],
    "marka": ["marka", "marka proizvoda", "robna marka", "brand"],
    "cijena": ["mpc", "maloprodajna cijena", "cijena", "price", "mpc eur", "maloprodajna cijena eur"],
    "posebna": ["posebna cijena", "akcijska cijena", "mpc za vrijeme posebnog oblika prodaje", "special price"],
    "jedinica": ["jedinica mjere", "mjerna jedinica", "jedinica", "jm", "unit"],
    "kolicina": ["neto kolicina", "kolicina", "neto kolicina proizvoda", "quantity"],
    "jedinicna": ["cijena za jedinicu mjere", "cijena jedinice mjere", "jedinicna cijena", "cijena po jedinici mjere", "unit price"],
    "barkod": ["barkod", "ean", "ean kod", "barcode"],
    "dostupnost": ["dostupnost", "dostupno", "raspolozivost"],
}

BROJ = r"(\d+(?:[.,]\d+)?)"
JED = r"(mm|cm|dm|m2|m²|m\^2|m3|m³|m\^3|m|mg|kg|g|gr|ml|cl|dl|l|kom|komad|t)(?![a-z0-9])"
RE_VISE = re.compile(rf"(\d+)\s*[x×]\s*{BROJ}\s*(kg|g|l|ml|m2|m²|m3|m³)(?![a-z0-9])", re.I)
RE_JEDNO = re.compile(rf"{BROJ}\s*{JED}", re.I)
# "60x60 cm", "120x60x10 cm": dimenzije, nikad količina pakiranja.
RE_DIMENZIJE = re.compile(rf"\d+(?:[.,]\d+)?(?:\s*[x×]\s*\d+(?:[.,]\d+)?)+\s*(mm|cm|m)(?![a-z0-9])", re.I)


def normaliziraj(tekst: str) -> str:
    tekst = (tekst or "").lower().replace("đ", "d")
    tekst = "".join(z for z in unicodedata.normalize("NFD", tekst) if not unicodedata.combining(z))
    return re.sub(r"[^a-z0-9]+", " ", tekst).strip()


def u_broj(vrijednost) -> float | None:
    """'1.234,56' i '1234.56' -> 1234.56; prazno/neispravno -> None."""
    if vrijednost is None:
        return None
    s = str(vrijednost).strip().replace(" ", "").replace(" ", "").replace("€", "").replace("EUR", "")
    if not s:
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    else:
        s = s.replace(",", ".")
    try:
        broj = float(s)
    except ValueError:
        return None
    return broj if math.isfinite(broj) and broj > 0 else None


def u_osnovnu(iznos: float, jedinica: str) -> tuple[float, str] | None:
    osnovna = JEDINICE.get((jedinica or "").strip().lower().rstrip("."))
    if not osnovna or not iznos or iznos <= 0:
        return None
    vrijednost = iznos * osnovna[1]
    if vrijednost > NAJVISE[osnovna[0]]:
        return None
    return round(vrijednost, 6), osnovna[0]


def iz_naziva(naziv: str) -> tuple[float, str] | None:
    """Količina iz naziva: '25 kg', '15 l', '2,5 m2/pak', '4x5 kg'. Dimenzije se preskaču."""
    tekst = RE_DIMENZIJE.sub(" ", naziv or "")
    if m := RE_VISE.search(tekst):
        jedno = u_osnovnu(u_broj(m.group(2)) or 0, m.group(3))
        if jedno:
            return u_osnovnu(int(m.group(1)) * jedno[0], jedno[1])
    for m in RE_JEDNO.finditer(tekst):
        jed = m.group(2).lower()
        # Samostalni mm/cm u nazivu opisuju debljinu ili promjer, ne količinu.
        if jed in ("mm", "cm", "dm"):
            continue
        if rezultat := u_osnovnu(u_broj(m.group(1)) or 0, jed):
            return rezultat
    return None


# Alat i oprema: broj u nazivu (čekić 500 g, libela 60 cm, ključ 10 mm) opisuje alat, ne količinu pakiranja.
RE_ALAT = re.compile(r"\b(cekic\w*|macol\w*|klijest\w*|kljuc\w*|odvijac\w*|busilic\w*|brusilic\w*|pila|pile|pilu|"
                     r"tester\w*|svrdl\w*|nastav\w*|bit|bitov\w*|lopat\w*|kolica|ljestv\w*|libel\w*|metar|"
                     r"skarp\w*|dlijet\w*|turpij\w*|gleteric\w*|zlic\w*|mistrij\w*|valjak|kist\w*|noz|nozevi|"
                     r"rezac|skare|mjesalic\w*|aparat\w*|alat\w*|set|garnitur\w*)\b")


def je_alat(naziv: str) -> bool:
    return bool(RE_ALAT.search(normaliziraj(naziv)))


def mjera(kolicina: str, jedinica: str, cijena: float | None, jedinicna: float | None, naziv: str):
    """
    (iznos, osnovna jedinica) ili None. Redoslijed: neto količina + jedinica mjere iz cjenika,
    zatim MPC / cijena za jedinicu mjere (oba obvezna u javnom cjeniku), pa naziv.
    """
    jedinica = (jedinica or "").strip().lower().rstrip(".")
    broj = u_broj(kolicina)
    if broj and jedinica in JEDINICE:
        if (r := u_osnovnu(broj, jedinica)) and not (r[1] == "kom" and r[0] == 1):
            return r
    elif kolicina and (m := RE_JEDNO.search(str(kolicina))):
        if r := u_osnovnu(u_broj(m.group(1)) or 0, m.group(2)):
            return r
    # Za "kom" cijena za jedinicu mjere obično je po kg/l/m², a ta jedinica nije zapisana.
    if cijena and jedinicna and jedinica in JEDINICE and JEDINICE[jedinica][0] != "kom":
        osnovna, faktor = JEDINICE[jedinica]
        # Cijena za jedinicu mjere odnosi se na zadanu jedinicu (npr. €/kg ili €/m²).
        iznos = round(cijena * faktor / jedinicna, 6)
        if 0 < iznos <= NAJVISE[osnovna] and not (osnovna == "kom" and abs(iznos - 1) < 1e-9):
            return iznos, osnovna
    if je_alat(naziv):
        return (1.0, "kom") if jedinica in ("kom", "komad", "kos") else None
    if r := iz_naziva(naziv):
        return r
    if jedinica in JEDINICE:
        osnovna, faktor = JEDINICE[jedinica]
        if faktor == 1:
            return 1.0, osnovna  # cijena je za jednu jedinicu mjere (vaga, metraža, komad)
    return None


SPEC = [
    (re.compile(r"\b(eps)\s*-?\s*(\d{2,3}|f|t)\b", re.I), lambda m: f"EPS {m.group(2).upper()}"),
    (re.compile(r"\bxps\b", re.I), lambda m: "XPS"),
    (re.compile(r"\bgrafit\w*", re.I), lambda m: "grafitni"),
    # Puna oznaka vrste cementa: CEM II/B-M (LL-V) nije isto što i CEM II/B-S.
    (re.compile(r"\bcem\s*(i{1,3}|iv|v)(?:\s*/\s*([abc]))?(?:\s*-\s*([a-z]{1,2}))?(?:\s*\(\s*([a-z]{1,2}(?:\s*-\s*[a-z]{1,2})*)\s*\))?(?![a-z])", re.I),
     lambda m: "CEM " + m.group(1).upper() + (f"/{m.group(2).upper()}" if m.group(2) else "")
     + (f"-{m.group(3).upper()}" if m.group(3) else "") + (f" ({re.sub(r'\s+', '', m.group(4)).upper()})" if m.group(4) else "")),
    # Razred čvrstoće cementa: 32,5 R i 42,5 N nisu isti proizvod.
    (re.compile(r"(?<![\d.,])(32|42|52)[.,]5\s*([rnl])?(?![a-z0-9])", re.I),
     lambda m: f"{m.group(1)},5" + (f" {m.group(2).upper()}" if m.group(2) else "")),
    # Ljepila za pločice (HRN EN 12004): C2TE S1 i C2TE S2 razlikuju se po deformabilnosti.
    (re.compile(r"\b(c[12])\s*(t)?\s*(e)?(?:\s*(s[12]))?(?![a-z0-9])", re.I),
     lambda m: (m.group(1) + (m.group(2) or "") + (m.group(3) or "")).upper() + (f" {m.group(4).upper()}" if m.group(4) else "")),
    (re.compile(r"\bc(\d{2})/(\d{2})\b", re.I), lambda m: f"C{m.group(1)}/{m.group(2)}"),
    (re.compile(r"(?:ø|fi|φ|dn)\s*(\d+(?:[.,]\d+)?)", re.I), lambda m: f"Ø{m.group(1).replace('.', ',')}"),
]
# Frakcija agregata: "pijesak 0-4 mm" i "4-8 mm" nisu usporedivi.
RE_FRAKCIJA = re.compile(r"(?<![\d.,])(\d+(?:[.,]\d+)?)\s*[-–/]\s*(\d+(?:[.,]\d+)?)\s*mm(?![a-z0-9])", re.I)
RE_DEBLJINA = re.compile(r"(?<![x×\d.,])(\d+(?:[.,]\d+)?)\s*(mm|cm)(?![a-z0-9])(?!\s*[x×])", re.I)


def specifikacija(naziv: str, jedinica: str) -> str:
    """Oznake koje moraju biti iste da bi se ponude uspoređivale po jedinici (debljina, razred, promjer)."""
    oznake = []
    for regex, oblik in SPEC:
        if m := regex.search(naziv or ""):
            oznake.append(oblik(m))
    if je_alat(naziv) and (m := RE_JEDNO.search(RE_DIMENZIJE.sub(" ", naziv or ""))):
        oznake.append(f"{m.group(1)} {m.group(2).lower()}")
    if m := RE_FRAKCIJA.search(naziv or ""):
        oznake.append(f"frakcija {m.group(1)}-{m.group(2)} mm".replace(".", ","))
    if jedinica in ("m", "m2", "m3", "kom"):
        bez_dimenzija = RE_DIMENZIJE.sub(lambda m: " ", RE_FRAKCIJA.sub(" ", naziv or ""))
        if m := RE_DEBLJINA.search(bez_dimenzija):
            mm = (u_broj(m.group(1)) or 0) * (10 if m.group(2).lower() == "cm" else 1)
            if mm and not any(o.startswith("Ø") for o in oznake):
                oznake.append(f"{mm:g} mm".replace(".", ","))
        if m := RE_DIMENZIJE.search(naziv or ""):
            oznake.append(re.sub(r"\s+", "", m.group(0)).replace("×", "x"))
    return " · ".join(dict.fromkeys(oznake))


def opis_mjere(iznos: float, jedinica: str) -> str:
    if jedinica == "kg" and iznos < 1:
        tekst, jed = f"{iznos * 1000:g}", "g"
    elif jedinica == "l" and iznos < 1:
        tekst, jed = f"{iznos * 1000:g}", "ml"
    else:
        tekst, jed = f"{iznos:g}", {"m2": "m²", "m3": "m³"}.get(jedinica, jedinica)
    return f"{tekst.replace('.', ',')} {jed}"


def broj_rijeci_marke(naziv: str, marka: str) -> int:
    n, m = normaliziraj(naziv).split(), normaliziraj(marka).split()
    return len(m) if m and len(n) > len(m) and n[: len(m)] == m else 0


# ---------- Čitanje cjenika ----------
def _kljuc_stupca(ime: str, vlastiti: dict) -> str | None:
    n = normaliziraj(ime)
    for kljuc, naziv in (vlastiti or {}).items():
        if normaliziraj(naziv) == n:
            return kljuc
    for kljuc, nazivi in STUPCI.items():
        if n in nazivi:
            return kljuc
    return None


def dekodiraj(sadrzaj: bytes) -> str:
    for kodiranje in ("utf-8-sig", "cp1250"):
        try:
            return sadrzaj.decode(kodiranje)
        except UnicodeDecodeError:
            continue
    return sadrzaj.decode("latin-1")


def citaj_csv(tekst: str, vlastiti: dict | None = None):
    uzorak = tekst[:4096]
    try:
        dijalekt = csv.Sniffer().sniff(uzorak, delimiters=";,\t|")
    except csv.Error:
        dijalekt = csv.excel
        dijalekt.delimiter = ";" if uzorak.count(";") > uzorak.count(",") else ","
    redovi = csv.reader(io.StringIO(tekst), dijalekt)
    zaglavlje = next(redovi, [])
    kljucevi = [_kljuc_stupca(z, vlastiti) for z in zaglavlje]
    if "naziv" not in kljucevi or "cijena" not in kljucevi:
        raise ValueError(f"CSV nema prepoznate stupce naziv i cijena: {zaglavlje}")
    for red in redovi:
        zapis = {k: v.strip() for k, v in zip(kljucevi, red) if k}
        if zapis.get("naziv"):
            yield zapis


def popravi_xml(tekst: str) -> str:
    """HTML entiteti (&nbsp;, &scaron;) i goli "&" u nazivima čine XML neispravnim; pretvaraju se u valjani XML."""
    def entitet(m):
        ime = m.group(1)
        if ime in ("amp", "lt", "gt", "quot", "apos"):
            return m.group(0)
        kod = html.entities.name2codepoint.get(ime)
        return chr(kod) if kod else "&amp;" + ime + ";"
    tekst = re.sub(r"&([A-Za-z][A-Za-z0-9]*);", entitet, tekst)
    return re.sub(r"&(?![A-Za-z][A-Za-z0-9]*;|#\d+;|#x[0-9A-Fa-f]+;)", "&amp;", tekst)


def citaj_xml(tekst: str, vlastiti: dict | None = None):
    korijen = ET.fromstring(popravi_xml(tekst).encode("utf-8"))
    nadjeno = False
    for el in korijen.iter():
        djeca = list(el)
        if not djeca:
            continue
        zapis = {}
        for d in djeca:
            k = _kljuc_stupca(re.sub(r"[_\-]", " ", d.tag.split("}")[-1]), vlastiti)
            if k and (d.text or "").strip():
                zapis[k] = d.text.strip()
        if zapis.get("naziv") and zapis.get("cijena"):
            nadjeno = True
            yield zapis
    if not nadjeno:
        raise ValueError("XML nema zapisa s nazivom i cijenom")


ZAGREB = ZoneInfo("Europe/Zagreb")


def datum_objave(vrijednost):
    """ISO datum/vrijeme ili DD.MM.GGGG. Vrijeme sa zonom pretvara se u datum po zagrebačkom vremenu."""
    tekst = str(vrijednost or "").strip()
    if m := re.fullmatch(r"(\d{1,2})\.(\d{1,2})\.(\d{4})\.?", tekst):
        return datetime(int(m.group(3)), int(m.group(2)), int(m.group(1))).date()
    try:
        trenutak = datetime.fromisoformat(tekst.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (trenutak.astimezone(ZAGREB) if trenutak.tzinfo else trenutak).date()


# Zaglavlje XML cjenika: atribut generirano / generated / datum ili <objekt><vremenska_oznaka>. "referentni_datum" je
# datum sidrene cijene, ne datum cjenika.
def datum_iz_xml(tekst: str):
    korijen = ET.fromstring(popravi_xml(tekst).encode("utf-8"))
    for vrijednost in (korijen.get("generirano"), korijen.get("generated"), korijen.get("datum"),
                       korijen.findtext("objekt/vremenska_oznaka")):
        if vrijednost and (d := datum_objave(vrijednost.strip())):
            return d
    return None


# ---------- Oglasi ----------
def ocijeni_oglas(o: dict, sada: datetime) -> tuple[bool, str]:
    """(rangira se?, razlog). Nepotpuni oglasi ostaju vidljivi, ali nikad nisu 'najpovoljniji'."""
    if o.get("cijenaNaUpit") or u_broj(o.get("cijena")) is None:
        return False, "cijena na upit ili nepoznata"
    if (o.get("valuta") or "").upper() != "EUR":
        return False, "cijena nije u eurima"
    if o.get("pregovaranje"):
        return False, "cijena po dogovoru"
    if o.get("stanje") not in ("novo", "rabljeno"):
        return False, "stanje nije navedeno"
    if not u_broj(o.get("kolicina")) or (o.get("jedinica") or "").lower() not in JEDINICE:
        return False, "količina ili jedinica nije navedena"
    if not (o.get("specifikacija") or "").strip():
        return False, "specifikacija nije navedena"
    if o.get("pdv") not in ("ukljucen", "nije-obveznik"):
        return False, "nije jasno je li PDV uključen"
    return True, ""


def oglas_aktivan(o: dict, sada: datetime) -> bool:
    if o.get("aktivno") is False or o.get("prodano"):
        return False
    try:
        provjereno = datetime.fromisoformat(str(o.get("provjereno")).replace("Z", "+00:00"))
    except ValueError:
        return False
    if provjereno.tzinfo is None:
        provjereno = provjereno.replace(tzinfo=timezone.utc)
    return sada - provjereno <= timedelta(days=OGLAS_VRIJEDI_DANA)


def kljuc_oglasa(o: dict) -> str:
    """Isti oglas objavljen na više oglasnika: isti naslov, cijena i mjesto."""
    return "|".join([normaliziraj(o.get("naziv")), f"{u_broj(o.get('cijena')) or 0:.2f}", normaliziraj(o.get("lokacija"))])


# ---------- Obrada ----------
def _procitaj(izvor: dict, sadrzaj) -> tuple[list, str]:
    tekst = dekodiraj(sadrzaj) if isinstance(sadrzaj, bytes) else sadrzaj
    if izvor.get("format") in ("oglasi-json", "web-json"):
        stavke = json.loads(tekst)
        if not isinstance(stavke, list):
            raise ValueError(f"{izvor['format']} mora biti popis zapisa")
        return stavke, tekst
    if izvor.get("format") == "xml":
        return list(citaj_xml(tekst, izvor.get("stupci"))), tekst
    return list(citaj_csv(tekst, izvor.get("stupci"))), tekst


def obradi(izvori: list[dict], ucitaj, sada: datetime | None = None, rezerva=None) -> tuple[dict, list[dict]]:
    """
    izvori: provjereni izvori iz izvori.json. ucitaj(izvor) -> bytes ili str sadržaj.
    rezerva(izvor) -> (sadržaj, datum) zadnjeg valjanog cjenika ili None; koristi se kad današnji sadržaj stigne,
    ali se ne može obraditi ili nema datum (npr. HTTP 200 s HTML-om). Zadana je ucitaj.rezerva ako postoji.
    Vraća (podaci za aplikaciju ili None, stanje svakog izvora).
    """
    rezerva = rezerva or getattr(ucitaj, "rezerva", None)
    sada = sada or datetime.now(timezone.utc)
    lanci, vrste, stanje, datumi_lanaca = [], [], [], []
    svi: dict[str, dict] = {}
    vidjeni_oglasi: dict[str, str] = {}
    datumi = []
    for izvor in izvori:
        zapis_stanja = {"id": izvor["id"], "naziv": izvor["naziv"], "vrsta": izvor.get("vrsta", "trgovina")}
        if izvor.get("greska_stranice"):
            stanje.append({**zapis_stanja, "uspjeh": False, "greska": izvor["greska_stranice"]})
            continue
        if izvor.get("url"):
            zapis_stanja["url"] = izvor["url"]
        if izvor.get("otkriveno"):
            zapis_stanja["otkriveno"] = True
        stavke = datum = None
        greska = ""
        try:
            stavke, tekst = _procitaj(izvor, ucitaj(izvor))
            # Datum objave: iz popisa datoteka ili iz zaglavlja XML-a, nikad vrijeme preuzimanja.
            if izvor.get("format") not in ("oglasi-json", "web-json"):
                datum = datum_objave(izvor.get("datum")) or (datum_iz_xml(tekst) if izvor.get("format") == "xml" else None)
                if datum is None:
                    raise ValueError("nepoznat datum cjenika")
        except Exception as e:  # noqa: BLE001 - jedan neispravan izvor ne ruši ostale
            greska, stavke = str(e)[:300], None
        if stavke is None and rezerva and not izvor.get("iz_predmemorije"):
            # Današnji sadržaj nije valjan: zadnji valjani cjenik s izvornim datumom, uz zapis današnjeg kvara.
            spremljeno = rezerva(izvor)
            if spremljeno:
                try:
                    stavke, tekst = _procitaj(izvor, spremljeno[0])
                    datum = datum_objave(spremljeno[1])
                    izvor["iz_predmemorije"], izvor["datum"] = True, spremljeno[1]
                    zapis_stanja["danasnja_greska"] = greska
                except Exception:  # noqa: BLE001
                    stavke = None
        if stavke is None:
            stanje.append({**zapis_stanja, "uspjeh": False, "greska": greska})
            continue
        if izvor.get("format") not in ("oglasi-json", "web-json"):
            zapis_stanja["datum"] = datum.isoformat()
            if izvor.get("iz_predmemorije"):
                zapis_stanja["iz_predmemorije"] = True  # današnji dohvat nije uspio
            if (sada.date() - datum).days > CJENIK_VRIJEDI_DANA:
                stanje.append({**zapis_stanja, "uspjeh": False, "greska": f"zastario cjenik od {datum.isoformat()}"})
                continue
            datumi.append(datum)

        idx = len(lanci)
        lanci.append(izvor["naziv"])
        vrste.append(izvor.get("vrsta", "trgovina"))
        datumi_lanaca.append(zapis_stanja.get("datum", ""))
        primljeno = prihvaceno = odbaceno = zastarjelo = duplikata = neuspordeno = nedostupno = negradjevinsko = 0
        spojeno_u_izvoru = barkod_druga_sifra = 0
        sifre_barkoda: dict[str, str] = {}
        for s in stavke:
            primljeno += 1
            meta = None
            if izvor.get("format") == "oglasi-json":
                if not oglas_aktivan(s, sada):
                    zastarjelo += 1
                    continue
                k = kljuc_oglasa(s)
                if k in vidjeni_oglasi:
                    duplikata += 1
                    continue
                vidjeni_oglasi[k] = izvor["id"]
                rangira, razlog = ocijeni_oglas(s, sada)
                cijena = u_broj(s.get("cijena"))
                if cijena is None or round(cijena, 2) <= 0.01:
                    # Bez cijene nema iznosa za zbroj; oglas se ne prikazuje kao ponuda s cijenom.
                    odbaceno += 1
                    continue
                naziv = str(s.get("naziv") or "").strip()
                m = u_osnovnu(u_broj(s.get("kolicina")) or 0, s.get("jedinica") or "") if rangira else None
                spec = str(s.get("specifikacija") or "").strip()
                meta = {"izvor": izvor["naziv"], "url": s.get("url") if str(s.get("url", "")).startswith("https://") else "",
                        "provjereno": str(s.get("provjereno"))[:10], "stanje": s.get("stanje") or "",
                        "napomena": " · ".join(x for x in [s.get("lokacija") or "", s.get("dostava") or ""] if x)}
                if not rangira or not m:
                    meta["razlog"] = razlog or "količina nije prepoznata"
                    neuspordeno += 1
                kljuc = f"oglas:{izvor['id']}:{s.get('id') or k}"
                marka = ""
            elif izvor.get("format") == "web-json":
                # Ponuda sa stranice proizvoda (schema.org): vrijeme provjere nije datum objave cijene.
                provjereno = datetime.fromisoformat(s["provjereno"])
                if (sada - provjereno).days > CJENIK_VRIJEDI_DANA:
                    zastarjelo += 1
                    continue
                cijena = u_broj(s.get("cijena"))
                if cijena is None or round(cijena, 2) <= 0.01:
                    odbaceno += 1
                    continue
                naziv = str(s.get("naziv") or "").strip()
                marka = s.get("marka") or ""
                m = mjera("", "", cijena, None, naziv)
                spec = specifikacija(naziv, m[1]) if m else ""
                meta = {"izvor": izvor["naziv"], "url": s.get("url") if str(s.get("url", "")).startswith("https://") else "",
                        "provjereno": s["provjereno"][:10],
                        "napomena": " · ".join(x for x in ["cijena sa stranice proizvoda", f"PDV {s['pdv']}" if s.get("pdv") else ""] if x)}
                if s.get("razlog") or not m:
                    meta["razlog"] = s.get("razlog") or "količina nije prepoznata"
                    m = None
                    neuspordeno += 1
                kljuc = (s.get("gtin") or "").strip() or f"{izvor['id']}:{s.get('sku') or s.get('url')}"
            else:
                # Proizvod koji trgovac navodi kao nedostupan ne može biti najpovoljnija ponuda.
                if normaliziraj(s.get("dostupnost", "")) in ("nedostupan", "nedostupno", "ne", "0"):
                    nedostupno += 1
                    continue
                cijene = [c for c in (u_broj(s.get("cijena")), u_broj(s.get("posebna"))) if c and round(c, 2) > 0.01]
                if not cijene:
                    odbaceno += 1
                    continue
                cijena = min(cijene)
                naziv = s["naziv"]
                # Mješovita trgovina (otkrivena): uvoze se samo artikli s građevinskim pojmom; ostali se broje.
                if izvor.get("samo_gradjevinski") and not je_gradjevinski(naziv):
                    negradjevinsko += 1
                    continue
                marka = s.get("marka", "")
                m = mjera(s.get("kolicina", ""), s.get("jedinica", ""), u_broj(s.get("cijena")), u_broj(s.get("jedinicna")), naziv)
                spec = specifikacija(naziv, m[1]) if m else ""
                # "KOM" bez poznatog sadržaja (npr. "GLET MASA 25/1") nije usporediv s drugim komadima,
                # osim kad specifikacija (dimenzije, promjer, razred) određuje što je jedan komad.
                if m == (1.0, "kom") and not u_broj(s.get("kolicina")) and not spec:
                    m = None
                barkod = valjan_barkod(s.get("barkod"))
                sifra = (s.get("sifra") or "").strip()
                kljuc = barkod or f"{izvor['id']}:{sifra or normaliziraj(naziv)}"
                # Isti barkod pod drugom šifrom u istom cjeniku: zasebni artikli (npr. nijanse, veličine), ne spajaju se.
                if barkod and sifra:
                    prva = sifre_barkoda.setdefault(barkod, sifra)
                    if prva != sifra:
                        kljuc = f"{barkod}|{izvor['id']}:{sifra}"
                        barkod_druga_sifra += 1
            prihvaceno += 1
            zapis = svi.get(kljuc)
            # Isti barkod s drugom količinom, jedinicom ili specifikacijom nije ista ponuda za usporedbu.
            if zapis is not None and (zapis["mjera"] != m or zapis["spec"] != spec):
                kljuc = f"{kljuc}|{m[0] if m else ''}{m[1] if m else ''}|{spec}"
                zapis = svi.get(kljuc)
            if zapis is None:
                zapis = svi[kljuc] = {"cijene": {}, "mjera": m, "spec": spec, "meta": meta, "najniza": None}
            if idx in zapis["cijene"]:
                spojeno_u_izvoru += 1  # isti proizvod (barkod/šifra, mjera, specifikacija) više puta u istom cjeniku
            if idx not in zapis["cijene"] or cijena < zapis["cijene"][idx]:
                zapis["cijene"][idx] = cijena
            if zapis["najniza"] is None or cijena < zapis["najniza"]:
                zapis["najniza"], zapis["naziv"], zapis["marka"] = cijena, naziv, marka
        if prihvaceno == 0:
            # Cjenik bez ijedne dostupne ponude ne postaje prazna trgovina u aplikaciji.
            lanci.pop(); vrste.pop(); datumi_lanaca.pop()
            stanje.append({**zapis_stanja, "uspjeh": False, "greska": "nema dostupnih ponuda", "primljeno": primljeno,
                           "nedostupno": nedostupno, "odbaceno": odbaceno, "zastarjelo": zastarjelo, "duplikata": duplikata,
                           **({"negradjevinsko": negradjevinsko} if izvor.get("samo_gradjevinski") else {})})
            continue
        stanje.append({**zapis_stanja, "uspjeh": True, "primljeno": primljeno, "prihvaceno": prihvaceno,
                       "odbaceno": odbaceno, "zastarjelo": zastarjelo, "duplikata": duplikata,
                       "neusporedeno": neuspordeno, "nedostupno": nedostupno, "spojeno_u_izvoru": spojeno_u_izvoru,
                       "barkod_druga_sifra": barkod_druga_sifra,
                       **({"negradjevinsko": negradjevinsko} if izvor.get("samo_gradjevinski") else {}), "lanac": idx})

    proizvodi = []
    for z in svi.values():
        iznos, jedinica = z["mjera"] or (0, "")
        cijene = sorted(z["cijene"].items(), key=lambda lc: lc[1])
        proizvodi.append([
            z["naziv"], opis_mjere(iznos, jedinica) if jedinica else "", iznos, jedinica,
            broj_rijeci_marke(z["naziv"], z["marka"]),
            [x for lanac, c in cijene for x in (lanac, round(c, 2))],
            z["spec"], z["meta"],
        ])
    proizvodi.sort(key=lambda p: p[5][1])
    # Ponude u aplikaciji po izvoru (jedinstveni proizvodi tog izvora) i usklađenost s prihvaćenim retcima.
    po_lancu = [0] * len(lanci)
    for z in svi.values():
        for lanac in z["cijene"]:
            po_lancu[lanac] += 1
    for st in stanje:
        if st.get("uspjeh"):
            st["ponuda_u_aplikaciji"] = po_lancu[st.pop("lanac")]
            if st["ponuda_u_aplikaciji"] != st["prihvaceno"] - st["spojeno_u_izvoru"]:
                raise AssertionError(f"neusklađeni brojevi za {st['id']}")
    if not proizvodi:
        return None, stanje
    # Datum aplikacije je najstariji uključeni cjenik, da se ne prikazuje svježije od izvora.
    return {"verzija": 2, "datum": (min(datumi) if datumi else sada.date()).isoformat(), "azurirano": sada.isoformat(timespec="minutes"),
            "lanci": lanci, "vrsteIzvora": vrste, "datumiLanaca": datumi_lanaca, "proizvodi": proizvodi}, stanje


# ---------- Stranice s popisom cjenika (NN 101/2026) ----------
# Naziv datoteke: <vrsta>_<adresa>_<trgovac>_<oznaka>_<DD.MM.GGGG>_<HH.MM.SS[.mmm]>.csv
# (trgovci pišu i DD-MM-GGGG_HH-MM ili GGGGMMDDTHHMMSS)
# Poveznica u navodnicima smije imati razmake (Top Alati); bez navodnika završava razmakom ili ">".
RE_DATOTEKA = re.compile(r"""href\s*=\s*(?:"([^"]+?\.(csv|xml))(?:[?#][^"]*)?"|'([^']+?\.(csv|xml))(?:[?#][^']*)?'|([^"'\s>]+?\.(csv|xml))(?=[\s>?#]))""", re.I)
RE_DATUM_DATOTEKE = re.compile(r"[_-](\d{2})[.-](\d{2})[.-](\d{4})(?:_(\d{2})[.-](\d{2})(?:[.-](\d{2}))?)?[^/]*\.(?:csv|xml)$", re.I)
RE_DATUM_KOMPAKTNO = re.compile(r"[_-]?(\d{4})(\d{2})(\d{2})[T-](\d{2})(\d{2})(\d{2})?[^/]*\.(?:csv|xml)$", re.I)


def cjenici_sa_stranice(html: str, stranica: str, oblik: str = "csv") -> list[dict]:
    """
    Najnoviji cjenik svake poslovnice s popisa datoteka. Datum je iz naziva datoteke (datum objave),
    a poslovnica je dio naziva prije datuma. Put se kodira (npr. "Većeslava") jer urllib ne prima Unicode.
    """
    najnoviji: dict[str, dict] = {}
    for pogodak in RE_DATOTEKA.findall(html):
        href, nastavak = next((pogodak[i], pogodak[i + 1]) for i in (0, 2, 4) if pogodak[i])
        if nastavak.lower() != oblik:
            continue
        put = urllib.parse.unquote(href.split("?")[0])
        ime = put.rsplit("/", 1)[-1]
        if m := RE_DATUM_DATOTEKE.search(ime):
            d, mj, g, h, mi, se = m.groups()
        elif m := RE_DATUM_KOMPAKTNO.search(ime):
            g, mj, d, h, mi, se = m.groups()
        else:
            continue  # bez datuma u nazivu (npr. stalni "cjenik.xml") datum objave nije poznat
        vrijeme = datetime(int(g), int(mj), int(d), int(h or 0), int(mi or 0), int(se or 0))
        # Zadnji broj prije datuma je broj pohrane koji raste sa svakom objavom, ne oznaka poslovnice.
        poslovnica = re.sub(r"_\d+$", "", ime[: m.start()])
        apsolutno = urllib.parse.urljoin(stranica, put)
        dijelovi = urllib.parse.urlsplit(apsolutno)
        url = urllib.parse.urlunsplit(dijelovi._replace(path=urllib.parse.quote(dijelovi.path, safe="/%._-~")))
        if poslovnica not in najnoviji or vrijeme > najnoviji[poslovnica]["vrijeme"]:
            najnoviji[poslovnica] = {"poslovnica": poslovnica, "url": url, "vrijeme": vrijeme, "datum": vrijeme.date().isoformat()}
    return sorted(najnoviji.values(), key=lambda x: x["poslovnica"])


def razlozi_izvore(izvori: list[dict], dohvati) -> list[dict]:
    """Izvor sa "stranica" + "popis": true postaje jedan izvor po poslovnici, s datumom iz naziva datoteke."""
    rezultat = []
    for izvor in izvori:
        if not izvor.get("popis"):
            rezultat.append(izvor)
            continue
        try:
            html = dekodiraj(dohvati(izvor["stranica"]))
        except Exception as e:  # noqa: BLE001 - nedostupna stranica bilježi se kao neuspjeli izvor
            rezultat.append({**izvor, "popis": False, "greska_stranice": f"popis cjenika nedostupan: {e}"[:300]})
            continue
        filtar = [normaliziraj(f) for f in izvor.get("poslovnice", [])]
        prije = len(rezultat)
        for c in cjenici_sa_stranice(html, izvor["stranica"], izvor.get("format", "csv")):
            ime = c["poslovnica"].replace("_", " ").strip()
            if filtar and not any(f in normaliziraj(ime) for f in filtar):
                continue
            rezultat.append({**izvor, "id": f"{izvor['id']}:{c['poslovnica']}", "naziv": f"{izvor['naziv']} · {ime}",
                             "url": c["url"], "datum": c["datum"], "popis": False, "roditelj": izvor["id"]})
        if len(rezultat) == prije:
            # Stranica se otvorila, ali bez prepoznatih datiranih datoteka: izvor ostaje vidljiv, a predmemorija ga može nadomjestiti.
            rezultat.append({**izvor, "popis": False, "greska_stranice": "na stranici popisa nema prepoznatih cjenika"})
    return rezultat


def brojke_uvoza(stanje: list[dict], podaci: dict | None) -> dict:
    """
    Definicije: ulazni redak = redak datoteke; prihvaćeni redak = dostupan, s cijenom, u opsegu;
    ponuda proizvod×izvor = prihvaćeni redci nakon spajanja istog proizvoda unutar istog cjenika;
    jedinstveni proizvod = isti barkod (ili šifra), mjera i specifikacija kroz sve izvore = jedan red u aplikaciji.
    """
    ok = [s for s in stanje if s.get("uspjeh")]
    b = {"ulaznih_redaka": sum(s.get("primljeno", 0) for s in stanje),
         "prihvacenih_redaka": sum(s["prihvaceno"] for s in ok),
         "spojeno_u_izvoru": sum(s["spojeno_u_izvoru"] for s in ok),
         "ponuda_proizvod_izvor": sum(len(p[5]) // 2 for p in podaci["proizvodi"]) if podaci else 0,
         "jedinstvenih_proizvoda": len(podaci["proizvodi"]) if podaci else 0}
    if b["ponuda_proizvod_izvor"] != b["prihvacenih_redaka"] - b["spojeno_u_izvoru"] or \
            b["ponuda_proizvod_izvor"] != sum(s["ponuda_u_aplikaciji"] for s in ok):
        raise AssertionError(f"neusklađeni ukupni brojevi: {b}")
    return b


def valjan_barkod(vrijednost) -> str:
    """EAN/GTIN (8, 12, 13 ili 14 znamenki, ne same nule). „0“, „000…“ i kratke oznake nisu barkod i ne spajaju artikle."""
    b = re.sub(r"\s+", "", str(vrijednost or ""))
    return b if re.fullmatch(r"\d{8}|\d{12,14}", b) and b.strip("0") else ""


def preuzmi_url(url: str, pokusaja: int = 3, cekanje: float = 2.0, timeout: float = 60) -> bytes:
    """Dohvat s ograničenim ponovnim pokušajima. 403/404 se ne ponavljaju: to je odbijen pristup, ne kvar."""
    zahtjev = urllib.request.Request(url, headers={"User-Agent": "najjeftiniji-gradjevinski-materijal/1 (javni cjenik)"})
    for pokusaj in range(pokusaja):
        try:
            with urllib.request.urlopen(zahtjev, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 404, 410) or pokusaj == pokusaja - 1:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            if pokusaj == pokusaja - 1:
                raise
        time.sleep(cekanje * 2 ** pokusaj)
    raise RuntimeError("nedostižno")


# ---------- Zadnji valjani cjenik ----------
def _datoteka_predmemorije(mapa: Path, izvor_id: str) -> Path:
    return mapa / (re.sub(r"[^A-Za-z0-9._-]+", "_", izvor_id) + ".bin")


def spremi_predmemoriju(mapa: Path, izvor: dict, sadrzaj: bytes, datum: str) -> None:
    mapa.mkdir(parents=True, exist_ok=True)
    put = _datoteka_predmemorije(mapa, izvor["id"])
    put.with_suffix(".tmp").write_bytes(sadrzaj)
    put.with_suffix(".tmp").replace(put)
    indeks_put = mapa / "indeks.json"
    indeks = json.loads(indeks_put.read_text(encoding="utf-8")) if indeks_put.exists() else {}
    indeks[izvor["id"]] = {k: izvor.get(k) for k in ("id", "naziv", "vrsta", "format", "url", "stranica")} | {
        "datum": datum, "roditelj": izvor.get("roditelj"), "spremljeno": datetime.now(timezone.utc).isoformat(timespec="minutes")}
    indeks_put.write_text(json.dumps(indeks, ensure_ascii=False, indent=1), encoding="utf-8")


def ucitaj_predmemoriju(mapa: Path) -> dict:
    indeks_put = mapa / "indeks.json"
    return json.loads(indeks_put.read_text(encoding="utf-8")) if indeks_put.exists() else {}


def s_predmemorijom(izvori: list[dict], ucitaj, mapa: Path):
    """
    Izvor koji se danas ne može dohvatiti koristi zadnji valjani cjenik s njegovim izvornim datumom.
    Provjera starosti u obradi() zatim isključuje cjenik stariji od CJENIK_VRIJEDI_DANA.
    Vraća (izvori, ucitaj, preuzeto) — preuzeto su današnji sadržaji za spremanje nakon uspješne obrade.
    """
    indeks = ucitaj_predmemoriju(mapa)
    rezultat = []
    for izvor in izvori:
        if izvor.get("greska_stranice"):
            # Popis cjenika nedostupan: zadnje poznate poslovnice tog izvora iz predmemorije.
            spremljeni = [v for v in indeks.values() if v.get("roditelj") == izvor["id"]]
            if spremljeni:
                rezultat.extend({**izvor, **v, "popis": False, "greska_stranice": None, "iz_predmemorije": True}
                                for v in spremljeni)
            else:
                rezultat.append(izvor)
        else:
            rezultat.append(izvor)
    preuzeto = {}

    def ucitaj_ili_predmemorija(izvor):
        if not izvor.get("iz_predmemorije"):
            try:
                sadrzaj = ucitaj(izvor)
                preuzeto[izvor["id"]] = sadrzaj
                return sadrzaj
            except Exception:
                if izvor["id"] not in indeks:
                    raise
        spremljeno = indeks.get(izvor["id"])
        if not spremljeno:
            raise RuntimeError("dohvat nije uspio, a zadnji valjani cjenik ne postoji")
        izvor["iz_predmemorije"] = True
        izvor["datum"] = spremljeno["datum"]
        return _datoteka_predmemorije(mapa, izvor["id"]).read_bytes()

    def rezerva(izvor):
        """Zadnji valjani cjenik kad je današnji sadržaj stigao, ali nije valjan."""
        spremljeno = indeks.get(izvor["id"])
        put = _datoteka_predmemorije(mapa, izvor["id"])
        return (put.read_bytes(), spremljeno["datum"]) if spremljeno and put.exists() else None
    ucitaj_ili_predmemorija.rezerva = rezerva
    return rezultat, ucitaj_ili_predmemorija, preuzeto


def objavi_atomski(podaci: dict, put: Path) -> None:
    """Novi cjenik zamjenjuje stari tek kad je cijeli zapisan i valjan."""
    if not (podaci.get("verzija") == 2 and podaci.get("proizvodi") and podaci.get("lanci")
            and len(podaci["lanci"]) == len(podaci.get("vrsteIzvora", [])) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", podaci["datum"])):
        raise ValueError("cjenik nije valjan; objava preskočena")
    privremeno = put.with_suffix(".tmp")
    privremeno.write_text(json.dumps(podaci, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    json.loads(privremeno.read_text(encoding="utf-8"))
    privremeno.replace(put)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--izvori", type=Path, default=IZVORI)
    ap.add_argument("--otkriveni", type=Path, help="site/data/otkriveni.json: automatski provjereni kandidati")
    ap.add_argument("--webshop", type=Path, help="site/data/webshop.json: pilot ponuda sa stranica proizvoda (schema.org)")
    ap.add_argument("--predmemorija", type=Path, default=PREDMEMORIJA)
    ap.add_argument("--lokalno", nargs="*", default=[], help="id=datoteka: koristi lokalnu datoteku umjesto preuzimanja")
    ap.add_argument("--datum", nargs="*", default=[], help="id=GGGG-MM-DD: datum objave cjenika s popisa datoteka izvora")
    a = ap.parse_args()
    svi_izvori = json.loads(a.izvori.read_text(encoding="utf-8"))["izvori"]
    lokalno = dict(x.split("=", 1) for x in a.lokalno)
    for izvor_id, datum in (x.split("=", 1) for x in a.datum):
        for i in svi_izvori:
            if i["id"] == izvor_id:
                i["datum"] = datum
    aktivni = [i for i in svi_izvori if i.get("omogucen") and i.get("status") == "provjereno"]
    preskoceni = [{"id": i["id"], "naziv": i["naziv"], "vrsta": i.get("vrsta", "trgovina"), "status": i.get("status"),
                   "napomena": i.get("napomena", "")} for i in svi_izvori if i not in aktivni]
    if a.otkriveni:
        from otkrivanje import domena, izvori_iz_otkrivanja
        poznate = {domena(i.get("stranica") or i.get("url") or "") for i in aktivni}
        aktivni += [i for i in izvori_iz_otkrivanja(a.otkriveni) if domena(i.get("stranica") or i.get("url")) not in poznate]
    web = {}
    if a.webshop and a.webshop.exists():
        from otkrivanje import domena as _dom
        poznate_web = {_dom(i.get("stranica") or i.get("url") or "") for i in aktivni}
        for dom, v in json.loads(a.webshop.read_text(encoding="utf-8")).get("ponude", {}).items():
            if dom in poznate_web:
                continue  # trgovac sa službenim CSV/XML cjenikom koristi cjenik
            web[f"web:{dom}"] = json.dumps(v["ponude"], ensure_ascii=False).encode()
            aktivni.append({"id": f"web:{dom}", "naziv": f"{v['naziv']} (web)", "vrsta": "trgovina", "format": "web-json",
                            "url": f"https://{dom}/", "status": "provjereno", "omogucen": True, "web": True})
    ucitaj = lambda izvor: web[izvor["id"]] if izvor["id"] in web else (
        Path(lokalno[izvor["id"]]).read_bytes() if izvor["id"] in lokalno else preuzmi_url(izvor["url"]))
    dohvati_stranicu = lambda url: next((Path(v).read_bytes() for k, v in lokalno.items() if k == url), None) or preuzmi_url(url)
    izvori, ucitaj, preuzeto = s_predmemorijom(razlozi_izvore(aktivni, dohvati_stranicu), ucitaj, a.predmemorija)
    podaci, stanje = obradi(izvori, ucitaj)
    po_id = {i["id"]: i for i in izvori}
    for s in stanje:
        # Sprema se samo današnji sadržaj koji je i obrađen; neispravan današnji sadržaj ne briše zadnji valjani.
        if s["uspjeh"] and s["id"] in preuzeto and not s.get("iz_predmemorije"):
            spremi_predmemoriju(a.predmemorija, po_id[s["id"]], preuzeto[s["id"]], s["datum"])
    brojke = brojke_uvoza(stanje, podaci)
    STANJE.parent.mkdir(parents=True, exist_ok=True)
    STANJE.write_text(json.dumps({"azurirano": datetime.now(timezone.utc).isoformat(timespec="minutes"), "brojke": brojke,
                                  "uvezeno": stanje, "nije-uvezeno": preskoceni}, ensure_ascii=False, indent=1), encoding="utf-8")
    for s in stanje:
        print(("OK " if s["uspjeh"] else "GREŠKA ") + json.dumps(s, ensure_ascii=False))
    from otkrivanje import domena
    uspjesni = {s["id"] for s in stanje if s["uspjeh"]}
    # Trgovac = domena (poslovnice istog trgovca broje se jednom).
    trgovci = {domena(i.get("stranica") or i.get("url") or i["id"]) for i in izvori if i["id"] in uspjesni}
    sazetak = (f"Trgovaca s valjanim cjenikom: {len(trgovci)} · poslovnica/izvora: {sum(s['uspjeh'] for s in stanje)} · "
               f"ulaznih redaka: {brojke['ulaznih_redaka']} · prihvaćenih redaka: {brojke['prihvacenih_redaka']} · "
               f"ponuda proizvod×izvor: {brojke['ponuda_proizvod_izvor']} · jedinstvenih proizvoda: {brojke['jedinstvenih_proizvoda']} · "
               f"iz predmemorije: {sum(1 for s in stanje if s.get('iz_predmemorije'))} · "
               f"od toga sa stranica proizvoda (pilot): {len({domena(i['url']) for i in izvori if i.get('web') and i['id'] in uspjesni})}")
    print(sazetak)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
            f.write(sazetak + "\n")
    print(f"Neuključeni izvori: {len(preskoceni)} (nisu provjereni ili su isključeni)")
    if podaci is None:
        print("Nema valjanih cjenika; postojeći cjenik se ne mijenja.")
        return 0
    objavi_atomski(podaci, IZLAZ)
    print(f"Gotovo: {len(podaci['proizvodi'])} jedinstvenih proizvoda iz {len(podaci['lanci'])} izvora -> {IZLAZ}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
