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


def normalize_birth_year(value):
    text = str(value or "").strip()
    return text if re.fullmatch(r"(?:19|20)\d{2}", text) else ""


def identity_key(item, known_years):
    name_key = normalize_name(item.get("atleta_nome") or "")
    year = normalize_birth_year(item.get("anno_nascita"))
    if year:
        # La coppia nome normalizzato + anno permette di unire la stessa persona
        # tra FISI e FIS senza fondere omonimi di età diversa.
        return f"{name_key}|year:{year}"

    # Lo stesso codice federale e lo stesso nome possono recuperare un unico
    # anno già noto da altri risultati. Se ci sono anni in conflitto, non
    # decidiamo quale atleta sia.
    origin = item.get("origine")
    field = "codice_fis" if origin == "FIS" else "codice_fisi"
    federal_code = str(item.get(field) or "").strip()
    if federal_code and federal_code.upper() not in ("N/D", "-", "0"):
        candidates = known_years[(name_key, origin, federal_code)]
        if len(candidates) == 1:
            return f"{name_key}|year:{next(iter(candidates))}"

    if item.get("origine") == "FISI" and item.get("codice_fisi"):
        return f"{name_key}|fisi:{str(item['codice_fisi']).strip()}"

    if item.get("origine") == "FIS" and item.get("codice_fis"):
        return f"{name_key}|fis:{str(item['codice_fis']).strip()}"

    # Fallback solo per record storici che non hanno ancora un identificativo.
    return f"{name_key}|unknown"


def search_text(value):
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def athlete_id(key):
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def safe_segment(value):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "").strip())


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
            codice_fisi,
            codice_fis,
            anno_nascita,
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

    known_years = defaultdict(set)
    with psycopg.connect(DATABASE_URL, connect_timeout=20) as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT origine, atleta_nome, codice_fisi, codice_fis, anno_nascita '
                        'FROM "Risultati_Unificati"')
            for origin, name, fisi, fis, birth in cur:
                year = normalize_birth_year(birth)
                name_key = normalize_name(name)
                federal_code = str((fis if origin == "FIS" else fisi) or "").strip()
                if year and name_key and federal_code and federal_code.upper() not in ("N/D", "-", "0"):
                    known_years[(name_key, origin, federal_code)].add(year)

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
                    name_key = normalize_name(name)
                    if not name_key:
                        skipped_results.append({
                            "origine": item.get("origine"),
                            "id_gara": item.get("id_gara"),
                            "atleta_nome": name,
                            "data_gara_iso": item.get("data_gara_iso"),
                        })
                        continue

                    key = identity_key(item, known_years)
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
                            "fisi_code": None,
                            "fis_code": None,
                            "birth_year": normalize_birth_year(item.get("anno_nascita")) or None,
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
                    if item.get("codice_fisi") and not group["fisi_code"]:
                        group["fisi_code"] = str(item["codice_fisi"])
                    if item.get("codice_fis") and not group["fis_code"]:
                        group["fis_code"] = str(item["codice_fis"])
                    if not group["birth_year"]:
                        group["birth_year"] = normalize_birth_year(item.get("anno_nascita")) or None
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
            "fisi_code": group["fisi_code"],
            "fis_code": group["fis_code"],
            "birth_year": group["birth_year"],
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

        search_parts = list(sorted(group["aliases"]))
        if group["birth_year"]:
            search_parts.append(group["birth_year"])
        if group["fisi_code"]:
            search_parts.append(group["fisi_code"])
        if group["fis_code"]:
            search_parts.append(group["fis_code"])

        index_items.append({
            "id": aid,
            "name": group["display_name"],
            "search": search_text(" ".join(search_parts)),
            "origins": sorted(group["origins"]),
            "fisi_code": group["fisi_code"],
            "fis_code": group["fis_code"],
            "birth_year": group["birth_year"],
            "nation": group["nation"],
            "count": len(results),
            "last_date": max(dates) if dates else None,
            "file": f"v1/{rel_file}",
        })

    # Classifiche per gara: usa le tabelle sorgente, così una classifica
    # resta completa anche quando la vista unificata sopprime un duplicato FISI/FIS.
    race_groups = defaultdict(list)

    race_queries = [
        (
            "FISI",
            """
            SELECT
                id_gara_fisi AS id_gara,
                atleta_nome,
                codice_fisi,
                anno_nascita,
                societa,
                comitato,
                categoria,
                specialita,
                posizione,
                tempo,
                gara_nome,
                luogo,
                data_gara,
                data_gara_iso
            FROM "Risultati"
            """
        ),
        (
            "FIS",
            """
            SELECT
                id_gara_fis AS id_gara,
                atleta_nome,
                codice_fis,
                anno_nascita,
                societa,
                comitato,
                categoria,
                specialita,
                posizione,
                tempo,
                gara_nome,
                luogo,
                data_gara,
                data_gara_iso
            FROM "Risultati_Fis"
            """
        ),
    ]

    with psycopg.connect(DATABASE_URL, connect_timeout=20) as conn:
        with conn.cursor() as cur:
            for origin, race_query in race_queries:
                cur.execute(race_query)
                columns = [d.name for d in cur.description]

                while True:
                    rows = cur.fetchmany(5000)
                    if not rows:
                        break

                    for row in rows:
                        item = {name: clean(value) for name, value in zip(columns, row)}
                        race_id = safe_segment(item.get("id_gara"))
                        if not race_id:
                            continue
                        item["origine"] = origin
                        item["id_gara"] = str(item["id_gara"])
                        race_groups[(origin, race_id)].append(item)

    for (origin, race_id), items in race_groups.items():
        write_json(
            OUTPUT_DIR / "v1" / "races" / origin.lower() / f"{race_id}.json",
            {
                "schema_version": 1,
                "origin": origin,
                "race_id": race_id,
                "count": len(items),
                "items": items,
            },
        )

    index_items.sort(key=lambda x: x["name"].casefold())

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    meta = {
        "schema_version": 1,
        "generated_at": generated_at,
        "athletes": len(index_items),
        "results": total_results,
        "skipped_results": len(skipped_results),
        "races": len(race_groups),
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
    print(f"File gara: {len(race_groups)}")
    print(f"Dimensione totale: {size_bytes / 1024 / 1024:.2f} MB")
    print(f"Generato: {generated_at}")


if __name__ == "__main__":
    main()
