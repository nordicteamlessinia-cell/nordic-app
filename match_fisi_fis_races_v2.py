import os
import re
import unicodedata
from collections import defaultdict

import psycopg

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL mancante")

MIN_SHARED = int(os.getenv("DEDUP_MIN_SHARED", "5"))
MIN_COVERAGE = float(os.getenv("DEDUP_MIN_COVERAGE", "0.30"))

def norm_name(value):
    s = unicodedata.normalize("NFKD", value or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    tokens = [t for t in s.split() if t]
    return " ".join(sorted(tokens))

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

    by_date_fisi = defaultdict(lambda: defaultdict(list))
    by_date_fis = defaultdict(lambda: defaultdict(list))

    for r in fisi:
        by_date_fisi[r[3]][str(r[0])].append(r)
    for r in fis:
        by_date_fis[r[3]][str(r[0])].append(r)

    candidates = []

    for day in sorted(set(by_date_fisi) & set(by_date_fis)):
        for fisi_id, frows in by_date_fisi[day].items():
            f_names = {norm_name(r[1]) for r in frows if norm_name(r[1])}
            if not f_names:
                continue

            for fis_id, xrows in by_date_fis[day].items():
                x_names = {norm_name(r[1]) for r in xrows if norm_name(r[1])}
                if not x_names:
                    continue

                shared = f_names & x_names
                denom = max(1, min(len(f_names), len(x_names)))
                coverage = len(shared) / denom

                if len(shared) < MIN_SHARED or coverage < MIN_COVERAGE:
                    continue

                candidates.append({
                    "date": day,
                    "fisi_id": fisi_id,
                    "fis_id": fis_id,
                    "shared": len(shared),
                    "coverage": coverage,
                    "fisi_n": len(f_names),
                    "fis_n": len(x_names),
                    "fisi_name": frows[0][4],
                    "fis_name": xrows[0][4],
                    "fisi_place": frows[0][5],
                    "fis_place": xrows[0][5],
                    "examples": sorted(shared)[:8],
                })

    candidates.sort(key=lambda p: (-p["shared"], -p["coverage"], str(p["date"])))

    print("=" * 105)
    print(
        f"CANDIDATI GARA FISI ↔ FIS: almeno {MIN_SHARED} atleti in comune, "
        f"copertura minima {MIN_COVERAGE:.0%}"
    )
    print("=" * 105)
    print(f"Totale coppie candidate: {len(candidates)}")

    for p in candidates[:200]:
        print(
            f"\n{p['date']} | FISI {p['fisi_id']} ↔ FIS {p['fis_id']} | "
            f"atleti comuni {p['shared']} | copertura {p['coverage']:.1%} | "
            f"FISI {p['fisi_n']} / FIS {p['fis_n']}"
        )
        print(f"  FISI: {p['fisi_name']} | {p['fisi_place']}")
        print(f"  FIS : {p['fis_name']} | {p['fis_place']}")
        for name in p["examples"]:
            print(f"    ✓ {name}")

if __name__ == "__main__":
    main()
