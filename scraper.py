import os
import requests
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BASE_URL = "https://comitati.fisi.org/wp-admin/admin-ajax.php"

def aggiorna_calendario_completo():
    params = {
        "action": "competizioni_get_all",
        "offset": 0,
        "limit": 100,
        "url": "https://comitati.fisi.org/veneto/calendario/",
        "idStagione": "2026", 
        "disciplina": "",
        "dataInizio": "01/06/2025",
        "dataFine": "30/05/2026"
    }

    all_gare = []
    print("--- 🚀 INIZIO DOWNLOAD CALENDARIO (CON LUOGO E DATA) ---")

    try:
        while True:
            r = requests.get(BASE_URL, params=params, timeout=30)
            data = r.json()
            if not data: break

            for item in data:
                all_gare.append({
                    "id_gara_fisi": str(item.get("idCompetizione")), 
                    "gara_nome": item.get("nome"),
                    "luogo": item.get("comune"),       # Pesca il luogo!
                    "data_gara": item.get("dataInizio") # Pesca la data!
                })
            params["offset"] += params["limit"]
        
        if all_gare:
            supabase.table("Gare").upsert(all_gare).execute()
            print(f"--- ✅ {len(all_gare)} GARE AGGIORNATE CON LUOGO E DATA! ---")
            
    except Exception as e:
        print(f"❌ ERRORE: {e}")

if __name__ == "__main__":
    aggiorna_calendario_completo()
