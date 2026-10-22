"""
Čita samo izbornike kategorija Njuškala (bez oglasa) radi hijerarhije kategorija: python scripts/kategorije_njuskalo.py
Poštuje robots.txt; 403/CAPTCHA se ne zaobilaze. Ispis: kategorije s URL-om i datumom provjere -> site/data/njuskalo-kategorije.json
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
from otkrivanje import AGENT, poveznice  # noqa: E402

POCETNE = ["https://www.njuskalo.hr/gradjenje-opremanje", "https://www.njuskalo.hr/gradevinski-materijal"]
IZLAZ = Path(__file__).resolve().parent.parent / "site" / "data" / "njuskalo-kategorije.json"
NAJVISE_PODSTRANICA = 40


def veze_s_tekstom(html: str, osnova: str) -> list[tuple[str, str]]:
    rezultat = []
    for m in re.finditer(r"<a\b([^>]*)>(.*?)</a>", html, re.I | re.S):
        veze = poveznice(m.group(1), osnova)
        tekst = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2))).strip()
        if veze and tekst:
            rezultat.append((veze[0].split("?")[0].split("#")[0], tekst[:80]))
    return rezultat


def kategorije(html: str, osnova: str) -> list[dict]:
    """Jednodijelne putanje na njuskalo.hr (oblik kategorija), bez filtera (upiti) i bez oglasa (brojevi u putanji)."""
    vidjeno, rezultat = set(), []
    for url, tekst in veze_s_tekstom(html, osnova):
        p = urllib.parse.urlsplit(url)
        if p.hostname != "www.njuskalo.hr" or not re.fullmatch(r"/[a-z0-9-]+", p.path) or re.search(r"-\d{6,}$", p.path):
            continue
        if url not in vidjeno and url.rstrip("/") != osnova.rstrip("/"):
            vidjeno.add(url)
            rezultat.append({"naziv": tekst, "url": url})
    return rezultat


def main():
    rp = urllib.robotparser.RobotFileParser()
    try:
        rp.parse(uvoz.dekodiraj(uvoz.preuzmi_url("https://www.njuskalo.hr/robots.txt", pokusaja=1)).splitlines())
    except Exception as e:  # noqa: BLE001
        print(f"robots.txt nedostupan: {e}")
        rp.parse([])
    sada = datetime.now(timezone.utc).isoformat(timespec="minutes")
    stranice = {}
    red = list(POCETNE)
    while red and len(stranice) < NAJVISE_PODSTRANICA:
        url = red.pop(0)
        if url in stranice:
            continue
        if not rp.can_fetch(AGENT, url):
            stranice[url] = {"greska": "robots.txt zabranjuje", "provjereno": sada}
            continue
        try:
            html = uvoz.dekodiraj(uvoz.preuzmi_url(url, pokusaja=1))
        except Exception as e:  # noqa: BLE001
            stranice[url] = {"greska": str(e)[:200], "provjereno": sada}
            continue
        k = kategorije(html, url)
        stranice[url] = {"naslov": (re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I) or [None, ""])[1].strip()[:120],
                         "bajtova": len(html), "poveznice": k, "provjereno": sada}
        if url == POCETNE[1]:  # jedna razina dublje samo za građevinski materijal
            red += [x["url"] for x in k]
    IZLAZ.parent.mkdir(parents=True, exist_ok=True)
    IZLAZ.write_text(json.dumps(stranice, ensure_ascii=False, indent=1), encoding="utf-8")
    for url, s in stranice.items():
        print(f"== {url}: " + (s.get("greska") or f"{s['naslov']} ({s['bajtova']} B, {len(s['poveznice'])} kategorijskih poveznica)"))
        for x in s.get("poveznice", []):
            print(f"   {x['naziv']} — {x['url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
