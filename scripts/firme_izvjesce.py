"""
Izvještaj po FIRMI iz stvarnog uvoza (ne po izvorima ni poslovnicama): za svaku firmu s prihvaćenim ponudama naziv, vrsta
izvora (službeni cjenik / webshop pilot), URL-ovi, datumi cijena, prihvaćene ponude i ponude u aplikaciji, unosi u
aplikaciji (prodajna mjesta s različitim cjenikom ostaju zasebna) te izvori bez ponuda s razlogom.

Čita site/data/stanje-izvora.json i site/data/proizvodi.json, piše site/data/firme-izvjesce.json i ispisuje tablicu.
Pokretanje (nakon scripts/uvoz.py):  python scripts/firme_izvjesce.py
"""

import json
import re
from pathlib import Path

KORIJEN = Path(__file__).resolve().parent.parent


def firma(naziv: str) -> str:
    return re.sub(r" \((web|oglasi)\)$", "", naziv.partition(" · ")[0]).strip()


def main():
    stanje = json.loads((KORIJEN / "site" / "data" / "stanje-izvora.json").read_text(encoding="utf-8"))
    podaci = json.loads((KORIJEN / "site" / "data" / "proizvodi.json").read_text(encoding="utf-8"))
    ponude_unosa = [0] * len(podaci["lanci"])
    for p in podaci["proizvodi"]:
        for k in range(0, len(p[5]), 2):
            ponude_unosa[p[5][k]] += 1
    firme_unosa = podaci.get("firmeLanaca") or [firma(x) for x in podaci["lanci"]]

    rez: dict[str, dict] = {}
    for s in stanje["uvezeno"]:
        f = rez.setdefault(firma(s["naziv"]), {"izvori": [], "bez_ponuda": [], "prihvaceno": 0, "vrste": set()})
        if s.get("uspjeh"):
            f["prihvaceno"] += int(s.get("prihvaceno") or 0)
            f["vrste"].add("webshop pilot (schema.org)" if str(s.get("id", "")).startswith("web:") else "službeni cjenik")
            f["izvori"].append({k: s.get(k) for k in ("naziv", "url", "datum", "prihvaceno", "ponuda_u_aplikaciji")})
        else:
            f["bez_ponuda"].append({"naziv": s["naziv"], "url": s.get("url"), "razlog": s.get("greska")})
    for i, ime in enumerate(firme_unosa):
        f = rez.setdefault(firma(ime), {"izvori": [], "bez_ponuda": [], "prihvaceno": 0, "vrste": set()})
        f.setdefault("unosi", []).append({"unos": podaci["lanci"][i], "ponuda": ponude_unosa[i]})

    s_ponudama = {k: v for k, v in rez.items() if v["prihvaceno"] > 0}
    izlaz = {"datum_cjenika": podaci["datum"], "firmi_s_prihvacenim_ponudama": len(s_ponudama),
             "unosa_u_aplikaciji": len(podaci["lanci"]),
             "firme": [{"firma": k, "vrsta": sorted(v["vrste"]), "prihvaceno": v["prihvaceno"],
                        "ponuda_u_aplikaciji": sum(u["ponuda"] for u in v.get("unosi", [])),
                        "unosi": v.get("unosi", []), "izvori": v["izvori"], "izvori_bez_ponuda": v["bez_ponuda"]}
                       for k, v in sorted(rez.items(), key=lambda x: -x[1]["prihvaceno"])]}
    (KORIJEN / "site" / "data" / "firme-izvjesce.json").write_text(json.dumps(izlaz, ensure_ascii=False, indent=1),
                                                                   encoding="utf-8")
    print(f"Firmi s prihvaćenim ponudama: {len(s_ponudama)} (unosa u aplikaciji: {len(podaci['lanci'])}), "
          f"cjenik od {podaci['datum']}")
    for f in izlaz["firme"]:
        datumi = sorted({i["datum"] for i in f["izvori"] if i.get("datum")})
        print(f"{'OK' if f['prihvaceno'] else '--'} {f['firma']} | {', '.join(f['vrsta']) or 'bez ponuda'} | "
              f"prihvaćeno {f['prihvaceno']} | u aplikaciji {f['ponuda_u_aplikaciji']} | unosa {len(f['unosi'])} | "
              f"datum {', '.join(datumi) or '-'}")
        for i in f["izvori"]:
            print(f"     izvor: {i['url']} ({i.get('datum') or 'datum nije objavljen'}, prihvaćeno {i['prihvaceno']})")
        for i in f["izvori_bez_ponuda"]:
            print(f"     bez ponuda: {i['naziv']} — {i['razlog']}")


if __name__ == "__main__":
    main()
