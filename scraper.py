import os
import requests
from supabase import create_client

# 1. Configurazione Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. Configurazione API FISI
BASE_URL = "https://comitati.fisi.org/wp-admin/admin-ajax.php"

def avvia_estrazione():
    params = {
        "action": "competizioni_get_all",
        "offset": 0,
        "limit": 100,
        "url": "https://comitati.fisi.org/veneto/calendario/",
        "idStagione": "2025",
        "disciplina": "",
        "dataInizio": "01/06/2025",
        "dataFine": "30/05/2026"
    }

    all_gare = []
    print("--- 🚀 INIZIO DOWNLOAD DALLE API FISI ---")

    while True:
        try:
            r = requests.get(BASE_URL, params=params, timeout=30)
            data = r.json()

            if not data or len(data) == 0:
                break

            for item in data:
                # Mappiamo i dati dell'API alle colonne della tua tabella Supabase
                # Verifica che i nomi delle colonne (a sinistra) siano quelli nel tuo DB
                all_gare.append({
                    "id_gara_fisi": str(item.get("idComp")),
                    "gara_nome": item.get("titolo"),
                    "localita": item.get("localita"),
                    "data": item.get("dataFine"), # o dataInizio
                    "societa": item.get("societa_desc")
                })

            params["offset"] += params["limit"]
            print(f"Scaricati {len(all_gare)} record...")

        except Exception as e:
            print(f"--- ❌ Errore durante la chiamata: {e} ---")
            break

    # 3. Invio a Supabase in blocco
    if all_gare:
        print(f"--- 💾 INVIO {len(all_gare)} RECORD A SUPABASE ---")
        try:
            # Assicurati che la tabella si chiami 'Gare'
            supabase.table("Gare").upsert(all_gare).execute()
            print("--- ✅ OPERAZIONE COMPLETATA CON SUCCESSO ---")
        except Exception as e:
            print(f"--- ❌ ERRORE DATABASE: {e} ---")
    else:
        print("--- ⚠️ Nessun dato trovato per i parametri impostati ---")

if __name__ == "__main__":
    avvia_estrazione()
