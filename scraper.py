import os
import requests
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BASE_URL = "https://comitati.fisi.org/wp-admin/admin-ajax.php"

def avvia_estrazione_calendario():
    params = {
        "action": "competizioni_get_all",
        "offset": 0,
        "limit": 100,
        "url": "https://comitati.fisi.org/veneto/calendario/",
        "idStagione": "2025", # Puoi cambiare in "2024" se vuoi scaricare l'anno scorso
        "disciplina": "",
        "dataInizio": "01/06/2024",
        "dataFine": "30/05/2026"
    }

    all_gare = []
    print("--- 🚀 INIZIO DOWNLOAD CALENDARIO (API PULITA) ---")

    try:
        while True:
            r = requests.get(BASE_URL, params=params, timeout=30)
            data = r.json()
            if not data: break

            for item in data:
                all_gare.append({
                    "id_gara_fisi": str(item.get("idComp")), # Questo estrae l'ID corretto a 5 cifre!
                    "gara_nome": item.get("titolo")
                    
                    # NOTA: Ho lasciato commentate 'localita' e 'societa' per evitare 
                    # il vecchio errore di colonna non trovata. 
                    # Se le hai create su Supabase con questi nomi esatti, togli il '#' qui sotto:
                    # , "localita": item.get("localita")
                    # , "societa": item.get("societa_desc")
                })
            params["offset"] += params["limit"]
            print(f"Scaricati {len(all_gare)} record competizioni...")

        if all_gare:
            print(f"--- 💾 INVIO {len(all_gare)} RECORD A SUPABASE ---")
            supabase.table("Gare").upsert(all_gare).execute()
            print("--- ✅ SUCCESSO TOTALE: CALENDARIO CARICATO! ---")
            
    except
