import os
import requests
from supabase import create_client

# Configurazione
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BASE_URL = "https://comitati.fisi.org/wp-admin/admin-ajax.php"

def scarica_risultati_atleti():
    # 1. Prendiamo le gare da Supabase per sapere quali ID scansionare
    print("--- 📚 RECUPERO ELENCO GARE DA DATABASE ---")
    gare_db = supabase.table("Gare").select("id_gara_fisi").execute()
    lista_id = [g['id_gara_fisi'] for g in gare_db.data]

    print(f"--- 🚀 INIZIO SCANSIONE DI {len(lista_id)} GARE ---")

    for id_gara in lista_id:
        params = {
            "action": "classifica_get",
            "idComp": id_gara
        }
        
        try:
            r = requests.get(BASE_URL, params=params, timeout=20)
            classifica = r.json()

            if not classifica or 'error' in classifica:
                continue

            batch_risultati = []
            # L'API classifica_get solitamente restituisce una lista di atleti
            for riga in classifica:
                batch_risultati.append({
                    "id_gara_fisi": id_gara,
                    "atleta_nome": riga.get("atleta_nome") or riga.get("nominativo"),
                    "posizione": riga.get("posizione"),
                    "societa": riga.get("societa_desc")
                })

            if batch_risultati:
                print(f"   ✅ Gara {id_gara}: Salvataggio {len(batch_risultati)} atleti...")
                supabase.table("Risultati").upsert(batch_risultati).execute()

        except Exception as e:
            print(f"   ❌ Errore nella gara {id_gara}: {e}")

if __name__ == "__main__":
    scarica_risultati_atleti()
