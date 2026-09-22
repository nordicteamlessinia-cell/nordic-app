import os
import re
from contextlib import contextmanager
from typing import Any

import psycopg
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL mancante")

app = FastAPI(
    title="Nordic Hub API",
    version="0.1.0",
    description="API read-only per risultati FISI/FIS di Nordic Hub",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://nordichub.web.app",
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:5000",
        "http://localhost:8000",
    ],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@contextmanager
def db():
    conn = psycopg.connect(DATABASE_URL, connect_timeout=20)
    try:
        yield conn
    finally:
        conn.close()


def clean_tokens(value: str) -> list[str]:
    text = re.sub(r"[^0-9A-Za-zÀ-ÿ' -]+", " ", value or "")
    return [t.lower() for t in re.split(r"\s+", text.strip()) if len(t) >= 2]


def name_key(value: str) -> str:
    text = (value or "").lower()
    text = re.sub(r"[^0-9a-zà-ÿ]+", " ", text)
    return " ".join(sorted(t for t in text.split() if t))


def name_where(tokens: list[str]) -> tuple[str, list[str]]:
    if not tokens:
        raise HTTPException(status_code=400, detail="Inserisci almeno 2 caratteri")
    clauses = []
    params: list[str] = []
    for token in tokens:
        clauses.append("lower(atleta_nome) LIKE %s")
        params.append(f"%{token}%")
    return " AND ".join(clauses), params


def row_to_dict(cur, row) -> dict[str, Any]:
    return {desc.name: value for desc, value in zip(cur.description, row)}


@app.get("/")
def root():
    return {
        "name": "Nordic Hub API",
        "version": "0.1.0",
        "endpoints": ["/health", "/athletes/search", "/athletes/results"],
    }


@app.get("/health")
def health():
    try:
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT count(*) FROM "Risultati_Unificati"')
                total = cur.fetchone()[0]
        return {"status": "ok", "database": "ok", "results_unified": total}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database non disponibile: {type(exc).__name__}")


@app.get("/athletes/search")
def athlete_search(
    q: str = Query(..., min_length=2, max_length=80),
    limit: int = Query(20, ge=1, le=50),
):
    tokens = clean_tokens(q)
    where_sql, params = name_where(tokens)

    sql = f"""
        SELECT atleta_nome, origine, codice_fis, nazione
        FROM "Risultati_Unificati"
        WHERE {where_sql}
        ORDER BY
            CASE WHEN lower(atleta_nome) LIKE %s THEN 0 ELSE 1 END,
            CASE WHEN origine = 'FISI' THEN 0 ELSE 1 END,
            atleta_nome
        LIMIT 250
    """
    params = params + [tokens[0] + "%"]

    try:
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Errore database: {type(exc).__name__}")

    # Deduplica nome/cognome invertiti, es. "Federico Pellegrino" e "PELLEGRINO Federico".
    unique: dict[str, dict[str, Any]] = {}
    for athlete_name, origin, fis_code, nation in rows:
        key = name_key(athlete_name)
        if not key:
            continue
        item = {
            "name": athlete_name,
            "origin": origin,
            "fis_code": fis_code or None,
            "nation": nation or None,
        }
        previous = unique.get(key)
        if previous is None:
            unique[key] = item
        elif previous["origin"] != "FISI" and origin == "FISI":
            unique[key] = item
        elif not previous.get("fis_code") and fis_code:
            # conserva il nome scelto ma arricchisce con codice FIS
            previous["fis_code"] = fis_code
            previous["nation"] = nation or previous.get("nation")

        if len(unique) >= limit:
            break

    return {"query": q, "count": len(unique), "items": list(unique.values())[:limit]}


@app.get("/athletes/results")
def athlete_results(
    q: str = Query(..., min_length=2, max_length=100),
    limit: int = Query(200, ge=1, le=1000),
):
    tokens = clean_tokens(q)
    where_sql, params = name_where(tokens)

    sql = f"""
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
        WHERE {where_sql}
        ORDER BY data_gara_iso DESC NULLS LAST, gara_nome, posizione
        LIMIT %s
    """
    params.append(limit)

    try:
        with db() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
                items = [row_to_dict(cur, row) for row in rows]
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Errore database: {type(exc).__name__}")

    for item in items:
        if item.get("data_gara_iso") is not None:
            item["data_gara_iso"] = item["data_gara_iso"].isoformat()

    return {"query": q, "count": len(items), "items": items}
