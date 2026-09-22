import os
import psycopg

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL mancante")

def show(cur, title, sql, limit=20):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)
    cur.execute(sql)
    rows = cur.fetchall()
    print(f"Righe: {len(rows)}")
    for row in rows[:limit]:
        print(" | ".join("" if x is None else str(x) for x in row))

def main():
    with psycopg.connect(DATABASE_URL, autocommit=True, connect_timeout=20) as conn:
        with conn.cursor() as cur:

            show(cur, "1) Duplicati INTERNI FISI con vecchia chiave nome+data+posizione", r"""
                SELECT
                    lower(trim(atleta_nome)) AS nome,
                    data_gara_iso,
                    upper(trim(posizione)) AS posizione,
                    count(*) AS n
                FROM "Risultati"
                WHERE data_gara_iso IS NOT NULL
                GROUP BY 1,2,3
                HAVING count(*) > 1
                ORDER BY n DESC, data_gara_iso DESC
                LIMIT 20
            """)

            show(cur, "2) Duplicati INTERNI FIS con vecchia chiave nome+data+posizione", r"""
                SELECT
                    lower(trim(atleta_nome)) AS nome,
                    data_gara_iso,
                    upper(trim(posizione)) AS posizione,
                    count(*) AS n
                FROM "Risultati_Fis"
                WHERE data_gara_iso IS NOT NULL
                GROUP BY 1,2,3
                HAVING count(*) > 1
                ORDER BY n DESC, data_gara_iso DESC
                LIMIT 20
            """)

            show(cur, "3) FISI/FIS stesso giorno + stessa posizione, nomi diversi", r"""
                SELECT
                    f.data_gara_iso,
                    f.atleta_nome AS fisi_nome,
                    x.atleta_nome AS fis_nome,
                    f.posizione,
                    f.gara_nome AS fisi_gara,
                    x.gara_nome AS fis_gara,
                    f.luogo AS fisi_luogo,
                    x.luogo AS fis_luogo
                FROM "Risultati" f
                JOIN "Risultati_Fis" x
                  ON f.data_gara_iso = x.data_gara_iso
                 AND upper(trim(f.posizione)) = upper(trim(x.posizione))
                WHERE lower(trim(f.atleta_nome)) <> lower(trim(x.atleta_nome))
                ORDER BY f.data_gara_iso DESC
                LIMIT 50
            """, 50)

            show(cur, "4) Possibili match con parole del nome invertite/riordinate", r"""
                WITH fisi AS (
                    SELECT
                        data_gara_iso, posizione, atleta_nome, gara_nome, luogo,
                        regexp_replace(lower(trim(atleta_nome)), '\\s+', ' ', 'g') AS nome_norm
                    FROM "Risultati"
                    WHERE data_gara_iso IS NOT NULL
                ),
                fis AS (
                    SELECT
                        data_gara_iso, posizione, atleta_nome, gara_nome, luogo,
                        regexp_replace(lower(trim(atleta_nome)), '\\s+', ' ', 'g') AS nome_norm
                    FROM "Risultati_Fis"
                    WHERE data_gara_iso IS NOT NULL
                )
                SELECT
                    f.data_gara_iso,
                    f.atleta_nome AS fisi_nome,
                    x.atleta_nome AS fis_nome,
                    f.posizione,
                    f.gara_nome AS fisi_gara,
                    x.gara_nome AS fis_gara
                FROM fisi f
                JOIN fis x
                  ON f.data_gara_iso = x.data_gara_iso
                 AND upper(trim(f.posizione)) = upper(trim(x.posizione))
                 AND (
                     f.nome_norm LIKE '%' || split_part(x.nome_norm, ' ', 1) || '%'
                     AND f.nome_norm LIKE '%' || split_part(x.nome_norm, ' ', 2) || '%'
                 )
                WHERE f.nome_norm <> x.nome_norm
                ORDER BY f.data_gara_iso DESC
                LIMIT 50
            """, 50)

            show(cur, "5) Stesso giorno: gare FISI e FIS in località simili", r"""
                SELECT DISTINCT
                    f.data_gara_iso,
                    f.luogo AS fisi_luogo,
                    x.luogo AS fis_luogo,
                    f.gara_nome AS fisi_gara,
                    x.gara_nome AS fis_gara
                FROM "Risultati" f
                JOIN "Risultati_Fis" x
                  ON f.data_gara_iso = x.data_gara_iso
                WHERE
                    lower(f.luogo) = lower(x.luogo)
                    OR lower(x.luogo) LIKE '%' || lower(f.luogo) || '%'
                    OR lower(f.luogo) LIKE '%' || lower(x.luogo) || '%'
                ORDER BY f.data_gara_iso DESC
                LIMIT 50
            """, 50)

if __name__ == "__main__":
    main()
