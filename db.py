import os
from datetime import datetime

import psycopg


DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL mancante: configura il secret GitHub Actions DATABASE_URL")


def connect():
    # Con sslmode=verify-full psycopg/libpq usa per default
    # ~/.postgresql/root.crt. I workflow GitHub scaricano qui il CA
    # ufficiale CockroachDB Cloud prima di avviare gli scraper.
    return psycopg.connect(DATABASE_URL, autocommit=True, connect_timeout=20)


def parse_date(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.upper() in {"N/D", "NULL", "NONE"}:
        return None

    for fmt in (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d.%m.%Y",
        "%Y/%m/%d",
        "%B %d, %Y",
        "%d %b %Y",
    ):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _text(value, default=""):
    if value is None:
        return default
    return str(value).strip()


def upsert_gare(rows):
    if not rows:
        return 0

    query = '''
        INSERT INTO "Gare" (
            id_gara_fisi, data_gara, data_gara_iso, gara_nome,
            luogo, comitato, disciplina, codice_societa
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (id_gara_fisi) DO UPDATE SET
            data_gara = excluded.data_gara,
            data_gara_iso = excluded.data_gara_iso,
            gara_nome = excluded.gara_nome,
            luogo = excluded.luogo,
            comitato = excluded.comitato,
            disciplina = excluded.disciplina,
            codice_societa = excluded.codice_societa,
            updated_at = now()
    '''

    values = [
        (
            _text(r.get("id_gara_fisi")),
            _text(r.get("data_gara"), "N/D"),
            parse_date(r.get("data_gara")),
            _text(r.get("gara_nome"), "Gara Senza Nome"),
            _text(r.get("luogo"), "N/D"),
            _text(r.get("comitato"), "N/D"),
            _text(r.get("disciplina"), "N/D"),
            _text(r.get("codice_societa")),
        )
        for r in rows
        if r.get("id_gara_fisi") is not None
    ]

    with connect() as conn:
        with conn.cursor() as cur:
            cur.executemany(query, values)
    return len(values)


def upsert_risultati_fisi(rows):
    if not rows:
        return 0

    query = '''
        INSERT INTO "Risultati" (
            id_gara_fisi, id_comp_collegata, atleta_nome, societa,
            comitato, categoria, posizione, tempo, gara_nome,
            specialita, luogo, data_gara, data_gara_iso
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (id_gara_fisi, atleta_nome, categoria, posizione)
        DO UPDATE SET
            id_comp_collegata = excluded.id_comp_collegata,
            societa = excluded.societa,
            comitato = excluded.comitato,
            tempo = excluded.tempo,
            gara_nome = excluded.gara_nome,
            specialita = excluded.specialita,
            luogo = excluded.luogo,
            data_gara = excluded.data_gara,
            data_gara_iso = excluded.data_gara_iso,
            updated_at = now()
    '''

    values = [
        (
            _text(r.get("id_gara_fisi")),
            _text(r.get("id_comp_collegata")),
            _text(r.get("atleta_nome"), "N/D"),
            _text(r.get("societa"), "N/D"),
            _text(r.get("comitato"), "N/D"),
            _text(r.get("categoria"), "Generale"),
            _text(r.get("posizione"), "N/D"),
            _text(r.get("tempo"), "N/D"),
            _text(r.get("gara_nome")),
            _text(r.get("specialita")),
            _text(r.get("luogo"), "N/D"),
            _text(r.get("data_gara"), "N/D"),
            parse_date(r.get("data_gara")),
        )
        for r in rows
        if r.get("id_gara_fisi") is not None and r.get("atleta_nome")
    ]

    with connect() as conn:
        with conn.cursor() as cur:
            cur.executemany(query, values)
    return len(values)


def upsert_risultati_fis(rows):
    if not rows:
        return 0

    query = '''
        INSERT INTO "Risultati_Fis" (
            id_gara_fis, atleta_nome, codice_fis, nazione, societa,
            comitato, categoria, specialita, posizione, tempo,
            punti_fis, gara_nome, luogo, data_gara, data_gara_iso
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (id_gara_fis, atleta_nome, categoria, posizione)
        DO UPDATE SET
            codice_fis = excluded.codice_fis,
            nazione = excluded.nazione,
            societa = excluded.societa,
            comitato = excluded.comitato,
            specialita = excluded.specialita,
            tempo = excluded.tempo,
            punti_fis = excluded.punti_fis,
            gara_nome = excluded.gara_nome,
            luogo = excluded.luogo,
            data_gara = excluded.data_gara,
            data_gara_iso = excluded.data_gara_iso,
            updated_at = now()
    '''

    values = [
        (
            _text(r.get("id_gara_fis")),
            _text(r.get("atleta_nome"), "N/D"),
            _text(r.get("codice_fis")),
            _text(r.get("nazione"), "N/D"),
            _text(r.get("societa"), "N/D"),
            _text(r.get("comitato"), "FIS"),
            _text(r.get("categoria"), "FIS"),
            _text(r.get("specialita"), "Cross-Country"),
            _text(r.get("posizione"), "N/D"),
            _text(r.get("tempo"), "N/D"),
            _text(r.get("punti_fis")),
            _text(r.get("gara_nome")),
            _text(r.get("luogo"), "N/D"),
            _text(r.get("data_gara"), "N/D"),
            parse_date(r.get("data_gara")),
        )
        for r in rows
        if r.get("id_gara_fis") is not None and r.get("atleta_nome")
    ]

    with connect() as conn:
        with conn.cursor() as cur:
            cur.executemany(query, values)
    return len(values)


def fisi_race_has_results(id_gara_fisi):
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT 1 FROM "Risultati" WHERE id_gara_fisi = %s LIMIT 1',
                (_text(id_gara_fisi),),
            )
            return cur.fetchone() is not None


def fis_race_has_results(id_gara_fis):
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'SELECT 1 FROM "Risultati_Fis" WHERE id_gara_fis = %s LIMIT 1',
                (_text(id_gara_fis),),
            )
            return cur.fetchone() is not None


def count_rows(table):
    if table not in {"Gare", "Risultati", "Risultati_Fis"}:
        raise ValueError("Tabella non ammessa")
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(f'SELECT count(*) FROM "{table}"')
            return cur.fetchone()[0]
