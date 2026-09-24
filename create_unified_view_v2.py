import os
import re
import unicodedata
import psycopg

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL mancante")

RACE_PAIRS = [
    ("14984943", "35406"),  # 2020-02-16 Val Casies
    ("16201087", "39671"),  # 2022-01-30 Marcialonga - gruppo principale
    ("16201088", "39670"),  # 2022-01-30 Marcialonga - gruppo femminile
]

def norm_name(value):
    s = unicodedata.normalize("NFKD", value or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    tokens = [t for t in s.split() if t]
    return " ".join(sorted(tokens))

def sql_string(value):
    return "'" + str(value).replace("'", "''") + "'"

def main():
    suppressed = []

    with psycopg.connect(DATABASE_URL, autocommit=True, connect_timeout=20) as conn:
        with conn.cursor() as cur:
            for fisi_id, fis_id in RACE_PAIRS:
                cur.execute(
                    """
                    SELECT atleta_nome, anno_nascita
                    FROM "Risultati"
                    WHERE id_gara_fisi = %s
                    """,
                    (fisi_id,),
                )
                fisi_rows = cur.fetchall()

                cur.execute(
                    """
                    SELECT atleta_nome, anno_nascita
                    FROM "Risultati_Fis"
                    WHERE id_gara_fis = %s
                    """,
                    (fis_id,),
                )
                fis_rows = cur.fetchall()

                def person_key(name, year):
                    return (norm_name(name), str(year or "").strip())

                fis_keys = {
                    person_key(name, year)
                    for name, year in fis_rows
                    if norm_name(name)
                }

                matched_fisi = sorted({
                    (name, str(year or "").strip())
                    for name, year in fisi_rows
                    if norm_name(name) and person_key(name, year) in fis_keys
                })

                print(
                    f"🔗 FISI {fisi_id} ↔ FIS {fis_id}: "
                    f"{len(matched_fisi)} atleti FISI sostituiti dalla fonte FIS",
                    flush=True,
                )

                for name, year in matched_fisi:
                    suppressed.append((fisi_id, name, year))

            if suppressed:
                values_sql = ",\n        ".join(
                    f"({sql_string(fisi_id)}::STRING, {sql_string(name)}::STRING, {sql_string(year)}::STRING)"
                    for fisi_id, name, year in suppressed
                )
                suppressed_cte = f"""
suppressed_fisi(id_gara_fisi, atleta_nome, anno_nascita) AS (
    VALUES
        {values_sql}
),
"""
            else:
                suppressed_cte = """
suppressed_fisi(id_gara_fisi, atleta_nome, anno_nascita) AS (
    SELECT NULL::STRING, NULL::STRING, NULL::STRING WHERE false
),
"""

            sql = f"""
DROP VIEW IF EXISTS "gare_uniche_completo";
DROP VIEW IF EXISTS "Risultati_Unificati";

CREATE VIEW "Risultati_Unificati" AS
WITH
{suppressed_cte}
fisi_kept AS (
    SELECT r.*
    FROM "Risultati" r
    WHERE NOT EXISTS (
        SELECT 1
        FROM suppressed_fisi s
        WHERE s.id_gara_fisi = r.id_gara_fisi
          AND s.atleta_nome = r.atleta_nome
          AND COALESCE(s.anno_nascita, '') = COALESCE(r.anno_nascita, '')
    )
)
SELECT
    'FISI'::STRING AS origine,
    r.id_gara_fisi::STRING AS id_gara,
    r.id_gara_fisi::STRING AS id_gara_fisi,
    NULL::STRING AS id_gara_fis,
    r.id_comp_collegata::STRING AS id_comp_collegata,
    r.atleta_nome::STRING AS atleta_nome,
    r.codice_fisi::STRING AS codice_fisi,
    NULL::STRING AS codice_fis,
    r.anno_nascita::STRING AS anno_nascita,
    NULL::STRING AS nazione,
    r.societa::STRING AS societa,
    r.comitato::STRING AS comitato,
    r.categoria::STRING AS categoria,
    r.specialita::STRING AS specialita,
    r.posizione::STRING AS posizione,
    r.tempo::STRING AS tempo,
    NULL::STRING AS punti_fis,
    r.gara_nome::STRING AS gara_nome,
    r.luogo::STRING AS luogo,
    r.data_gara::STRING AS data_gara,
    r.data_gara_iso AS data_gara_iso
FROM fisi_kept r

UNION ALL

SELECT
    'FIS'::STRING AS origine,
    r.id_gara_fis::STRING AS id_gara,
    NULL::STRING AS id_gara_fisi,
    r.id_gara_fis::STRING AS id_gara_fis,
    NULL::STRING AS id_comp_collegata,
    r.atleta_nome::STRING AS atleta_nome,
    NULL::STRING AS codice_fisi,
    r.codice_fis::STRING AS codice_fis,
    r.anno_nascita::STRING AS anno_nascita,
    r.nazione::STRING AS nazione,
    r.societa::STRING AS societa,
    r.comitato::STRING AS comitato,
    r.categoria::STRING AS categoria,
    r.specialita::STRING AS specialita,
    r.posizione::STRING AS posizione,
    r.tempo::STRING AS tempo,
    r.punti_fis::STRING AS punti_fis,
    r.gara_nome::STRING AS gara_nome,
    r.luogo::STRING AS luogo,
    r.data_gara::STRING AS data_gara,
    r.data_gara_iso AS data_gara_iso
FROM "Risultati_Fis" r;

CREATE VIEW "gare_uniche_completo" AS
SELECT * FROM "Risultati_Unificati";
"""
            cur.execute(sql)

            cur.execute('SELECT count(*) FROM "Risultati"')
            fisi = cur.fetchone()[0]
            cur.execute('SELECT count(*) FROM "Risultati_Fis"')
            fis = cur.fetchone()[0]
            cur.execute('SELECT count(*) FROM "Risultati_Unificati"')
            unified = cur.fetchone()[0]
            cur.execute('SELECT count(*) FROM "Risultati_Unificati" WHERE origine = \'FISI\'')
            unified_fisi = cur.fetchone()[0]
            cur.execute('SELECT count(*) FROM "Risultati_Unificati" WHERE origine = \'FIS\'')
            unified_fis = cur.fetchone()[0]

            print("\n✅ Vista unificata v2 creata", flush=True)
            print(f"📊 FISI originali: {fisi}", flush=True)
            print(f"📊 FIS originali: {fis}", flush=True)
            print(f"📊 Totale sorgenti: {fisi + fis}", flush=True)
            print(f"📊 Unificati v2: {unified}", flush=True)
            print(f"🧹 Sole righe FISI sostituite da FIS: {(fisi + fis) - unified}", flush=True)
            print(f"   ↳ FISI mantenuti: {unified_fisi}", flush=True)
            print(f"   ↳ FIS mantenuti: {unified_fis}", flush=True)

            print("\n🔎 Coppie gara gestite:", flush=True)
            for fisi_id, fis_id in RACE_PAIRS:
                print(f"   FISI {fisi_id} ↔ FIS {fis_id}", flush=True)

if __name__ == "__main__":
    main()
