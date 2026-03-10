import os
import requests
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BASE_URL = "https://comitati.fisi.org/wp-admin/admin-ajax.php"

def avvia_estrazione_calendario_corretta():
    params = {
        "action": "competizioni_get_all",
        "offset": 0,
        "limit": 100,
        "url": "https://comitati.fisi.org/veneto/calendario/",
        "idStagione": "2025", 
        "disciplina": "",
        "dataInizio": "01/06/2024",
        "dataFine": "30/05/2026"
    }

    all_gare = []
    print("--- 🚀 INIZIO DOWNLOAD CALENDARIO ---")

    try:
        while True:
            r = requests.get(BASE_URL, params=params, timeout=30)
            data = r.json()
            if not data: break

            for item in data:
                # Usiamo FINAMENTE le etichette giuste!
                record = {
                    "id_gara_fisi": str(item.get("idCompetizione")), 
                    "gara_nome": item.get("nome")
                }
                
                # Se nel tuo DB hai le colonne "localita" e "data_gara", 
                # togli il '#' dalle due righe qui sotto per salvarle:
                # record["localita"] = item.get("comune")
                # record["data_gara"] = item.get("dataInizio")
                
                all_gare.append(record)
                
            params["offset"] += params["limit"]
            print(f"Scaricati {len(all_gare)} record competizioni...")

        if all_gare:
            print(f"--- 💾 INVIO {len(all_gare)} RECORD A SUPABASE ---")
            supabase.table("Gare").upsert(all_gare).execute()
            print("--- ✅ SUCCESSO TOTALE: CALENDARIO CARICATO! ---")
            
    except Exception as e:
        print(f"--- ❌ ERRORE: {e} ---")

if __name__ == "__main__":
    avvia_estrazione_calendario_corretta()
