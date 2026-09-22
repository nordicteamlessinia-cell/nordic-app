import os
import psycopg

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL mancante")

SQL = r'''
DROP VIEW IF EXISTS "gare_uniche_completo";
DROP VIEW IF EXISTS "Risultati_Unificati";

CREATE VIEW "Risultati_Unificati" AS
WITH combined AS (
    SELECT
        'FISI'::STRING AS origine,
        r.id_gara_fisi::STRING AS id_gara,
        r.id_gara_fisi::STRING AS id_gara_fisi,
        NULL::STRING AS id_gara_fis,
        r.id_comp_collegata::STRING AS id_comp_collegata,
        r.atleta_nome::STRING AS atleta_nome,
        NULL::STRING AS codice_fis,
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
    FROM "Risultati" r

    UNION ALL

    SELECT
        'FIS'::STRING AS origine,
        r.id_gara_fis::STRING AS id_gara,
        NULL::STRING AS id_gara_fisi,
        r.id_gara_fis::STRING AS id_gara_fis,
        NULL::STRING AS id_comp_collegata,
        r.atleta_nome::STRING AS atleta_nome,
        r.codice_fis::STRING AS codice_fis,
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
    FROM "Risultati_Fis" r
),
ranked AS (
    SELECT
        c.*,
        row_number() OVER (
            PARTITION BY
                lower(
                    replace(
                        replace(
                            replace(trim(c.atleta_nome), '  ', ' '),
                        '  ', ' '),
                    '  ', ' ')
                ),
                COALESCE(
                    CAST(c.data_gara_iso AS STRING),
                    c.origine || ':' || c.id_gara
                ),
                upper(trim(c.posizione))
            ORDER BY
                CASE WHEN c.origine = 'FIS' THEN 0 ELSE 1 END,
                CASE WHEN COALESCE(c.codice_fis, '') <> '' THEN 0 ELSE 1 END,
                c.id_gara
        ) AS dedup_rank
    FROM combined c
)
SELECT
    origine,
    id_gara,
    id_gara_fisi,
    id_gara_fis,
    id_comp_collegata,
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
FROM ranked
WHERE dedup_rank = 1;

CREATE VIEW "gare_uniche_completo" AS
SELECT * FROM "Risultati_Unificati";
'''

QA = r'''
SELECT
    (SELECT count(*) FROM "Risultati") AS fisi,
    (SELECT count(*) FROM "Risultati_Fis") AS fis,
    (SELECT count(*) FROM "Risultati_Unificati") AS unificati,
    (SELECT count(*) FROM "Risultati_Unificati" WHERE origine = 'FIS') AS unificati_fis,
    (SELECT count(*) FROM "Risultati_Unificati" WHERE origine = 'FISI') AS unificati_fisi
'''

SAMPLES = r'''
SELECT
    f.data_gara_iso,
    f.atleta_nome,
    f.posizione,
    f.id_gara_fisi,
    x.id_gara_fis,
    f.gara_nome AS gara_fisi,
    x.gara_nome AS gara_fis
FROM "Risultati" f
JOIN "Risultati_Fis" x
  ON f.data_gara_iso = x.data_gara_iso
 AND lower(replace(replace(replace(trim(f.atleta_nome), '  ', ' '), '  ', ' '), '  ', ' '))
     = lower(replace(replace(replace(trim(x.atleta_nome), '  ', ' '), '  ', ' '), '  ', ' '))
 AND upper(trim(f.posizione)) = upper(trim(x.posizione))
ORDER BY f.data_gara_iso DESC
LIMIT 20
'''

def main():
    print("==============================================")
    print("NORDIC HUB - CREAZIONE VISTA RISULTATI UNIFICATI")
    print("==============================================")

    with psycopg.connect(DATABASE_URL, autocommit=True, connect_timeout=20) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
            print("✅ Viste create: Risultati_Unificati + gare_uniche_completo", flush=True)

            cur.execute(QA)
            fisi, fis, unificati, ufis, ufisi = cur.fetchone()
            print(f"📊 FISI: {fisi}", flush=True)
            print(f"📊 FIS: {fis}", flush=True)
            print(f"📊 Totale sorgenti: {fisi + fis}", flush=True)
            print(f"📊 Unificati: {unificati}", flush=True)
            print(f"🧹 Record eliminati come cloni: {(fisi + fis) - unificati}", flush=True)
            print(f"   ↳ mantenuti FIS: {ufis}", flush=True)
            print(f"   ↳ mantenuti FISI: {ufisi}", flush=True)

            cur.execute(SAMPLES)
            rows = cur.fetchall()
            print(f"🔎 Esempi sovrapposizioni FISI/FIS: {len(rows)}", flush=True)
            for row in rows:
                print(
                    f"   {row[0]} | {row[1]} | pos {row[2]} | "
                    f"FISI {row[3]} ↔ FIS {row[4]}",
                    flush=True,
                )

if __name__ == "__main__":
    main()
