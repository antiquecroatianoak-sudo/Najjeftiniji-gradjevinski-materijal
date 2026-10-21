"""
Dijagnoza spajanja redaka unutar istog cjenika na stvarnim podacima: python scripts/uzorak_spajanja.py [id izvora]
Za izvore iz zadnjeg uvoza (site/data/stanje-izvora.json) sa spojenim retcima preuzima isti cjenik, grupira retke istim
ključem kao uvoz (barkod ili šifra/naziv, mjera, specifikacija) i ispisuje sirove retke grupa te razlike unutar grupa
(naziv, cijena, posebna cijena, jedinica, ostali stupci). Ne mijenja podatke.
"""
import csv
import io
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import uvoz  # noqa: E402


def analiziraj(izvor_id: str, url: str, fmt: str, najvise_grupa: int = 8) -> dict:
    tekst = uvoz.dekodiraj(uvoz.preuzmi_url(url, pokusaja=2))
    if fmt != "csv":
        return {"id": izvor_id, "napomena": "samo CSV za sirovi uzorak"}
    dijalekt = csv.Sniffer().sniff(tekst[:4096], delimiters=";,\t|")
    redovi = list(csv.reader(io.StringIO(tekst), dijalekt))
    zaglavlje, sirovi = redovi[0], redovi[1:]
    kljucevi = [uvoz._kljuc_stupca(z, None) for z in zaglavlje]
    grupe = defaultdict(list)
    for red in sirovi:
        z = {k: v.strip() for k, v in zip(kljucevi, red) if k}
        if not z.get("naziv") or uvoz.normaliziraj(z.get("dostupnost", "")) in ("nedostupan", "nedostupno", "ne", "0"):
            continue
        m = uvoz.mjera(z.get("kolicina", ""), z.get("jedinica", ""), uvoz.u_broj(z.get("cijena")), uvoz.u_broj(z.get("jedinicna")), z["naziv"])
        spec = uvoz.specifikacija(z["naziv"], m[1]) if m else ""
        kljuc = (z.get("barkod") or f"{z.get('sifra') or uvoz.normaliziraj(z['naziv'])}", m, spec)
        grupe[kljuc].append(red)
    spojene = {k: v for k, v in grupe.items() if len(v) > 1}
    razlike = Counter()
    for v in spojene.values():
        for i, ime in enumerate(zaglavlje):
            if len({r[i] if i < len(r) else "" for r in v}) > 1:
                razlike[ime] += 1
    velicine = Counter(len(v) for v in spojene.values())
    primjeri = sorted(spojene.items(), key=lambda kv: -len(kv[1]))[:najvise_grupa]
    return {"id": izvor_id, "url": url, "zaglavlje": zaglavlje, "redaka_dostupnih": sum(len(v) for v in grupe.values()),
            "grupa": len(grupe), "grupa_sa_spajanjem": len(spojene), "spojeno_redaka": sum(len(v) - 1 for v in spojene.values()),
            "velicine_grupa": dict(sorted(velicine.items())[:15]), "stupci_koji_se_razlikuju_u_grupi": dict(razlike.most_common()),
            "primjeri": [{"kljuc": str(k), "retci": v[:6]} for k, v in primjeri]}


def main():
    stanje = json.loads(uvoz.STANJE.read_text(encoding="utf-8"))["uvezeno"]
    trazeni = set(sys.argv[1:])
    rezultat = []
    for s in stanje:
        if s.get("uspjeh") and s.get("spojeno_u_izvoru") and (not trazeni or s["id"] in trazeni):
            fmt = "csv" if s["url"].lower().split("?")[0].endswith(".csv") else "xml"
            try:
                rezultat.append(analiziraj(s["id"], s["url"], fmt))
            except Exception as e:  # noqa: BLE001
                rezultat.append({"id": s["id"], "greska": str(e)[:200]})
    izlaz = uvoz.STANJE.parent / "uzorak-spajanja.json"
    izlaz.write_text(json.dumps(rezultat, ensure_ascii=False, indent=1), encoding="utf-8")
    for r in rezultat:
        print(f"== {r['id']}: " + json.dumps({k: v for k, v in r.items() if k not in ("primjeri", "id")}, ensure_ascii=False)[:1500])
        for p in r.get("primjeri", [])[:5]:
            print(f"   ključ {p['kljuc'][:120]}")
            for red in p["retci"][:4]:
                print("     " + " | ".join(red)[:400])
    return 0


if __name__ == "__main__":
    sys.exit(main())
