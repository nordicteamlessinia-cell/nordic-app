import os
import re
import unicodedata
from collections import defaultdict

import psycopg

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL mancante")

MIN_SHARED = int(os.getenv("DEDUP_MIN_SHARED", "3"))

def norm_name(value):
    s = unicodedata.normalize("NFKD", value or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    tokens = [t for t in s.split() if t]
    return " ".join(sorted(tokens))

def norm_pos(value):
    s = (value or "").strip().upper()
    for code in ("DNS", "DNF", "DSQ", "LAP", "NPS"):
        if code in s:
            return code
    m = re.search(r"\d+", s)
    return m.group(0) if m else s[:3]

def main():
    with psycopg.connect(DATABASE_URL, autocommit=True, connect_timeout=20) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id_gara_fisi, atleta_nome, posizione, data_gara_iso, gara_nome, luogo
                FROM "Risultati"
                WHERE data_gara_iso IS NOT NULL
            """)
            fisi = cur.fetchall()

            cur.execute("""
                SELECT id_gara_fis, atleta_nome, posizione, data_gara_iso, gara_nome, luogo
                FROM "Risultati_Fis"
                WHERE data_gara_iso IS NOT NULL
            """)
            fis = cur.fetchall()

    by_date_fisi = defaultdict(list)
    by_date_fis = defaultdict(list)

    for row in fisi:
        by_date_fisi[row[3]].append(row)
    for row in fis:
        by_date_fis[row[3]].append(row)

    pairs = []

    for day in sorted(set(by_date_fisi) & set(by_date_fis)):
        f_groups = defaultdict(list)
        x_groups = defaultdict(list)

        for r in by_date_fisi[day]:
            f_groups[r[0]].append(r)
        for r in by_date_fis[day]:
            x_groups[r[0]].append(r)

        for fisi_id, frows in f_groups.items():
            fset = {(norm_name(r[1]), norm_pos(r[2])) for r in frows}
            if not fset:
                continue

            for fis_id, xrows in x_groups.items():
                xset = {(norm_name(r[1]), norm_pos(r[2])) for r in xrows}
                shared = fset & xset
                if len(shared) < MIN_SHARED:
                    continue

                # Rapporto sul lato più piccolo: serve per capire se è davvero la stessa gara.
                denom = max(1, min(len(fset), len(xset)))
                ratio = len(shared) / denom

                pairs.append({
                    "date": day,
                    "fisi_id": str(fisi_id),
                    "fis_id": str(fis_id),
                    "shared": len(shared),
                    "ratio": ratio,
                    "fisi_n": len(fset),
                    "fis_n": len(xset),
                    "fisi_name": frows[0][4],
                    "fis_name": xrows[0][4],
                    "fisi_place": frows[0][5],
                    "fis_place": xrows[0][5],
                    "examples": sorted(shared)[:5],
                })

    pairs.sort(key=lambda p: (-p["shared"], -p["ratio"], str(p["date"])))

    print("=" * 100)
    print(f"CANDIDATI GARA FISI ↔ FIS con almeno {MIN_SHARED} atleti coincidenti")
    print("=" * 100)
    print(f"Totale coppie candidate: {len(pairs)}")

    for p in pairs[:100]:
        print(
            f"\n{p['date']} | FISI {p['fisi_id']} ↔ FIS {p['fis_id']} | "
            f"match {p['shared']} | copertura {p['ratio']:.1%}"
        )
        print(f"  FISI: {p['fisi_name']} | {p['fisi_place']}")
        print(f"  FIS : {p['fis_name']} | {p['fis_place']}")
        for name, pos in p["examples"]:
            print(f"    ✓ {name} | pos {pos}")

if __name__ == "__main__":
    main()
