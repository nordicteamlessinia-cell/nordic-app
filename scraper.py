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
        "idStagione": "2025", # <-- TORNATO A 2025 COME IN ORIGINE!
        "disciplina": "",
        "dataInizio": "01/06/2024",
        "dataFine": "30/05/2026"
    }

    all_gare = []
    print("--- 🚀 INIZIO AGGIORNAMENTO CALENDARIO (LUOGO E DATA) ---")

    try:
        while True:
            r = requests.get(BASE_URL, params=params, timeout=30)
            data = r.json()
            if not data: break

            for item in data:
                record = {
                    "id_gara_fisi": str(item.get("idCompetizione")), 
                    "gara_nome": item.get("nome"),
                    "luogo": item.get("comune", "N/D"),       
                    "data_gara": item.get("dataInizio", "N/D") 
                }
                all_gare.append(record)
                
                # Stampiamo a video il primo record per fare la prova del 9
                if len(all_gare) == 1:
                    print(f"🔍 Test Lettura: {record['gara_nome']}")
                    print(f"📍 Luogo trovato: {record['luogo']} | 📅 Data trovata: {record['data_gara']}")

            params["offset"] += params["limit"]
        
        if all_gare:
            # L'upsert sovrascriverà le tue 131 righe aggiungendo i dati mancanti
            supabase.table("Gare").upsert(all_gare).execute()
            print(f"--- ✅ {len(all_gare)} GARE AGGIORNATE SU SUPABASE! ---")
            
    except Exception as e:
        print(f"❌ ERRORE: {e}")

if __name__ == "__main__":
    aggiorna_calendario_completo()
