import os
import psycopg

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL mancante")


def main():
    statements = [
        'ALTER TABLE "Risultati" ADD COLUMN IF NOT EXISTS codice_fisi STRING',
        'ALTER TABLE "Risultati" ADD COLUMN IF NOT EXISTS anno_nascita STRING',
        'ALTER TABLE "Risultati_Fis" ADD COLUMN IF NOT EXISTS anno_nascita STRING',
        'CREATE INDEX IF NOT EXISTS risultati_codice_fisi_idx ON "Risultati" (codice_fisi)',
        'CREATE INDEX IF NOT EXISTS risultati_anno_nascita_idx ON "Risultati" (anno_nascita)',
        'CREATE INDEX IF NOT EXISTS risultati_fis_anno_nascita_idx ON "Risultati_Fis" (anno_nascita)',
    ]

    with psycopg.connect(DATABASE_URL, autocommit=True, connect_timeout=20) as conn:
        with conn.cursor() as cur:
            for sql in statements:
                print(f"▶ {sql}", flush=True)
                cur.execute(sql)

            cur.execute("""
                SELECT
                    count(*) FILTER (WHERE codice_fisi IS NOT NULL AND codice_fisi <> ''),
                    count(*) FILTER (WHERE anno_nascita IS NOT NULL AND anno_nascita <> '')
                FROM "Risultati"
            """)
            fisi_code, fisi_year = cur.fetchone()

            cur.execute("""
                SELECT
                    count(*) FILTER (WHERE anno_nascita IS NOT NULL AND anno_nascita <> '')
                FROM "Risultati_Fis"
            """)
            fis_year = cur.fetchone()[0]

    print("✅ Migrazione identità atleta completata", flush=True)
    print(f"   FISI con codice: {fisi_code}", flush=True)
    print(f"   FISI con anno nascita: {fisi_year}", flush=True)
    print(f"   FIS con anno nascita: {fis_year}", flush=True)


if __name__ == "__main__":
    main()
