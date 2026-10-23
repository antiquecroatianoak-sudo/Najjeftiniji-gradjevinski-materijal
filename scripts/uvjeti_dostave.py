"""
Prikupljanje službenih uvjeta dostave s web stranica firmi (samo za ručnu provjeru, ništa se ne uvozi automatski).

Za svaku domenu (uključeni izvori i webshop pilot) dohvaća naslovnu stranicu, traži poveznice na stranice o dostavi
ili općim uvjetima i ispisuje rečenice o dostavi, iznosima i područjima doslovno, s URL-om i datumom dohvata.
Poštuje robots.txt; blokade (403, izazov) se ne zaobilaze nego bilježe. Iz ovog ispisa čovjek ili pregled izrađuje
scripts/dostava.json (samo potvrđena pravila s URL-om, datumom i citatom).

Pokretanje:  python scripts/uvjeti_dostave.py [domena ...]
"""

import html
import json
import re
import sys
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import datetime, timezone
from pathlib import Path

KORIJEN = Path(__file__).resolve().parent.parent
AGENT = "najjeftiniji-gradjevinski-materijal/1 (uvjeti dostave, rucna provjera)"
RE_POVEZNICA = re.compile(r"""<a\b[^>]*href\s*=\s*["']([^"'#]+)["'][^>]*>(.*?)</a>""", re.I | re.S)
RE_STRANICA = re.compile(r"dostav|isporuk|uvjeti|opci|opći|terms|shipping|delivery|nacin|način", re.I)
RE_RECENICA = re.compile(r"dostav|isporuk|besplatn|poštarin|postarin|prijevoz|€|eur\b|kn\b|minimal|palet|istovar|kamion", re.I)


def dohvati(url: str) -> str:
    zahtjev = urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept-Language": "hr"})
    with urllib.request.urlopen(zahtjev, timeout=30) as r:
        return r.read(2_000_000).decode("utf-8", "replace")


def tekst(stranica: str) -> str:
    stranica = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", stranica)
    stranica = re.sub(r"(?i)<br\s*/?>|</(p|li|div|h\d|tr)>", "\n", stranica)
    return html.unescape(re.sub(r"<[^>]+>", " ", stranica))


def recenice(t: str) -> list[str]:
    rez = []
    for red in re.split(r"\n+|(?<=[.!?])\s+", t):
        red = re.sub(r"\s+", " ", red).strip()
        if 12 <= len(red) <= 400 and RE_RECENICA.search(red) and red not in rez:
            rez.append(red)
    return rez


def domene() -> list[str]:
    izvori = json.loads((KORIJEN / "scripts" / "izvori.json").read_text(encoding="utf-8"))["izvori"]
    rez = []
    for i in izvori:
        if i.get("omogucen") or i.get("status") in ("provjereno", "blokirano"):
            u = i.get("stranica") or i.get("url") or ""
            if u:
                rez.append(urllib.parse.urlsplit(u).netloc)
    web = json.loads((KORIJEN / "scripts" / "webshopovi.json").read_text(encoding="utf-8"))["trgovci"]
    rez += [t.get("host") or t["domena"] for t in web]
    return list(dict.fromkeys(d for d in rez if d))


def obradi_domenu(domena: str) -> dict:
    osnova = f"https://{domena}/"
    rez = {"domena": domena, "dohvaceno": datetime.now(timezone.utc).isoformat(timespec="minutes"), "stranice": []}
    rp = urllib.robotparser.RobotFileParser(osnova + "robots.txt")
    try:
        rp.read()
    except Exception:  # noqa: BLE001
        rp = None
    dopusteno = lambda u: rp is None or rp.can_fetch(AGENT, u)  # noqa: E731
    try:
        naslovna = dohvati(osnova)
    except Exception as e:  # noqa: BLE001
        rez["greska"] = str(e)[:200]
        return rez
    kandidati = []
    for href, oznaka in RE_POVEZNICA.findall(naslovna):
        url = urllib.parse.urljoin(osnova, html.unescape(href))
        if urllib.parse.urlsplit(url).netloc.endswith(domena.removeprefix("www.")) and RE_STRANICA.search(href + " " + oznaka):
            kandidati.append(url)
    for url in list(dict.fromkeys(kandidati))[:6]:
        if not dopusteno(url):
            rez["stranice"].append({"url": url, "greska": "robots.txt ne dopušta"})
            continue
        try:
            r = recenice(tekst(dohvati(url)))
            rez["stranice"].append({"url": url, "recenice": r[:25]})
        except Exception as e:  # noqa: BLE001
            rez["stranice"].append({"url": url, "greska": str(e)[:200]})
    return rez


def main():
    ciljevi = sys.argv[1:] or domene()
    sve = [obradi_domenu(d) for d in ciljevi]
    izlaz = KORIJEN / "site" / "data" / "uvjeti-dostave-kandidati.json"
    izlaz.parent.mkdir(parents=True, exist_ok=True)
    izlaz.write_text(json.dumps(sve, ensure_ascii=False, indent=1), encoding="utf-8")
    for d in sve:
        print(f"===== {d['domena']} {d.get('greska', '')}")
        for s in d["stranice"]:
            print(f"  -- {s['url']} {s.get('greska', '')}")
            for r in s.get("recenice", []):
                print(f"     | {r}")


if __name__ == "__main__":
    main()
