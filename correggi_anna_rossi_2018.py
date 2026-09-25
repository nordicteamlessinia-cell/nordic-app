"""Corregge l'unico risultato FIS attribuito erroneamente ad Anna Rossi.

Eseguire una sola volta, con DATABASE_URL configurato, prima di riesportare
l'API statica. Non modifica le altre atlete della stessa classifica.
"""

from db import connect


WHERE = '''
    data_gara_iso = DATE '2018-12-02'
    AND lower(trim(atleta_nome)) = 'rossi anna'
    AND posizione = '5'
    AND coalesce(nullif(trim(codice_fis), ''), 'N/D') = 'N/D'
    AND coalesce(nullif(trim(tempo), ''), 'N/D') = 'N/D'
    AND strpos(lower(luogo), 'santa caterina') > 0
'''


def main():
    with connect() as conn:
        # db.connect() uses autocommit; the explicit transaction makes the
        # cardinality check and update atomic.
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    'SELECT id_gara_fis, atleta_nome, categoria, posizione, '
                    'codice_fis, tempo FROM "Risultati_Fis" WHERE ' + WHERE
                )
                rows = cur.fetchall()
                if len(rows) != 1:
                    raise RuntimeError(
                        f"Attesa una sola riga errata; trovate {len(rows)}: {rows!r}. "
                        "Nessuna modifica effettuata."
                    )
                print('Riga da correggere:', rows[0], flush=True)
                cur.execute(
                    'UPDATE "Risultati_Fis" '
                    "SET posizione = 'DNS', codice_fis = '3295447', "
                    "anno_nascita = '2001', updated_at = now() "
                    'WHERE ' + WHERE + ' RETURNING id_gara_fis, atleta_nome, '
                    'posizione, codice_fis, anno_nascita'
                )
                changed = cur.fetchall()
                if len(changed) != 1:
                    raise RuntimeError('Aggiornamento inatteso; transazione annullata')
                print('Riga corretta:', changed[0], flush=True)


if __name__ == '__main__':
    main()
