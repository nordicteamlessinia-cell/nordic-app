import hashlib
import json
import os
import re
import shutil
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import psycopg

DATABASE_URL = os.environ.get("DATABASE_URL")
OUTPUT_DIR = Path(os.environ.get("STATIC_API_OUTPUT", "static_api"))

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL mancante")


def normalize_name(value):
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    tokens = [token for token in text.split() if token]
    return " ".join(sorted(tokens))


def search_text(value):
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def athlete_id(key):
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def display_score(name, origin):
    # Preferisci il formato FISI e nomi non completamente maiuscoli.
    return (
        2 if origin == "FISI" else 0,
        1 if name and name != name.upper() else 0,
        len(name or ""),
    )


def clean(value):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )


def main():
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    query = """
        SELECT
            origine,
            id_gara,
            atleta_nome,
            codice_fis,
            nazione,
            societa,
            comitato,
            categoria,
            specialita,
            posizione,
            tempo,
            punti_fis,
            gara_nome,
            luogo,
            data_gara,
            data_gara_iso
        FROM "Risultati_Unificati"
        ORDER BY data_gara_iso DESC NULLS LAST, atleta_nome, id_gara
    """

    groups = {}
    total_results = 0
    skipped_results = []

    with psycopg.connect(DATABASE_URL, connect_timeout=20) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            columns = [d.name for d in cur.description]

            while True:
                rows = cur.fetchmany(5000)
                if not rows:
                    break

                for row in rows:
                    item = {name: clean(value) for name, value in zip(columns, row)}
                    name = (item.get("atleta_nome") or "").strip()
                    key = normalize_name(name)
                    if not key:
                        skipped_results.append({
                            "origine": item.get("origine"),
                            "id_gara": item.get("id_gara"),
                            "atleta_nome": name,
                            "data_gara_iso": item.get("data_gara_iso"),
                        })
                        continue

                    group = groups.get(key)
                    if group is None:
                        aid = athlete_id(key)
                        group = {
                            "id": aid,
                            "key": key,
                            "display_name": name,
                            "display_score": display_score(name, item.get("origine")),
                            "aliases": set(),
                            "origins": set(),
                            "fis_code": None,
                            "nation": None,
                            "results": [],
                        }
                        groups[key] = group

                    score = display_score(name, item.get("origine"))
                    if score > group["display_score"]:
                        group["display_name"] = name
                        group["display_score"] = score

                    group["aliases"].add(name)
                    if item.get("origine"):
                        group["origins"].add(item["origine"])
                    if item.get("codice_fis") and not group["fis_code"]:
                        group["fis_code"] = str(item["codice_fis"])
                    if item.get("nazione") and item["nazione"] not in ("N/D", ""):
                        group["nation"] = item["nazione"]

                    group["results"].append(item)
                    total_results += 1

    index_items = []

    for key, group in groups.items():
        aid = group["id"]
        shard = aid[:2]
        rel_file = f"athletes/data/{shard}/{aid}.json"
        results = group["results"]

        payload = {
            "schema_version": 1,
            "id": aid,
            "name": group["display_name"],
            "aliases": sorted(group["aliases"], key=str.casefold),
            "origins": sorted(group["origins"]),
            "fis_code": group["fis_code"],
            "nation": group["nation"],
            "count": len(results),
            "results": results,
        }
        write_json(OUTPUT_DIR / "v1" / rel_file, payload)

        dates = [
            r.get("data_gara_iso")
            for r in results
            if r.get("data_gara_iso")
        ]

        index_items.append({
            "id": aid,
            "name": group["display_name"],
            "search": search_text(" ".join(sorted(group["aliases"]))),
            "origins": sorted(group["origins"]),
            "fis_code": group["fis_code"],
            "nation": group["nation"],
            "count": len(results),
            "last_date": max(dates) if dates else None,
            "file": f"v1/{rel_file}",
        })

    index_items.sort(key=lambda x: x["name"].casefold())

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    meta = {
        "schema_version": 1,
        "generated_at": generated_at,
        "athletes": len(index_items),
        "results": total_results,
        "skipped_results": len(skipped_results),
    }

    write_json(
        OUTPUT_DIR / "v1" / "athletes" / "index.json",
        {
            "schema_version": 1,
            "generated_at": generated_at,
            "count": len(index_items),
            "items": index_items,
        },
    )
    write_json(OUTPUT_DIR / "v1" / "meta.json", meta)

    (OUTPUT_DIR / "index.html").write_text(
        """<!doctype html><html><head><meta charset="utf-8"><title>Nordic Hub Static API</title></head>
<body><h1>Nordic Hub Static API</h1><p>API JSON statica generata da GitHub Actions.</p>
<p><a href="v1/meta.json">meta.json</a> · <a href="v1/athletes/index.json">athletes/index.json</a></p></body></html>""",
        encoding="utf-8",
    )

    size_bytes = sum(p.stat().st_size for p in OUTPUT_DIR.rglob("*") if p.is_file())
    print("==============================================")
    print("NORDIC HUB - EXPORT API JSON")
    print("==============================================")
    print(f"Atleti unici: {len(index_items)}")
    print(f"Risultati esportati: {total_results}")
    print(f"Risultati saltati per nome non indicizzabile: {len(skipped_results)}")
    for row in skipped_results[:20]:
        print(
            f"  SKIP | {row['origine']} | gara {row['id_gara']} | "
            f"nome={row['atleta_nome']!r} | data={row['data_gara_iso']}",
            flush=True,
        )
    print(f"File atleta: {len(index_items)}")
    print(f"Dimensione totale: {size_bytes / 1024 / 1024:.2f} MB")
    print(f"Generato: {generated_at}")


if __name__ == "__main__":
    main()
