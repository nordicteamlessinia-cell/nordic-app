import os
import requests
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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
    print("--- 🚀 INIZIO DOWNLOAD API ---")

    while True:
        r = requests.get(BASE_URL, params=params)
        data = r.json()
        if not data: break

        for item in data:
            all_gare.append({
                "id_gara_fisi": str(item.get("idComp")),
                "gara_nome": item.get("titolo"),
                "localita": item.get("localita"),
                "societa": item.get("societa_desc")
                # Ho rimosso "data" per evitare l'errore PGRST204
            })
        params["offset"] += params["limit"]
        print(f"Scaricati {len(all_gare)} record...")

    if all_gare:
        print(f"--- 💾 INVIO {len(all_gare)} RECORD A SUPABASE ---")
        try:
            supabase.table("Gare").upsert(all_gare).execute()
            print("--- ✅ SUCCESSO TOTALE! ---")
        except Exception as e:
            print(f"--- ❌ ERRORE: {e} ---")

if __name__ == "__main__":
    avvia_estrazione()
