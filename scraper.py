import os
import requests
from supabase import create_client

# 1. Configurazione Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Referer': 'https://comitati.fisi.org/veneto/calendario/?d='
}

def avvia_scraper_serio():
    # Questo è l'URL segreto che restituisce i dati grezzi del calendario
    # senza passare per la grafica del sito
    url_sorgente = "https://comitati.fisi.org/veneto/wp-admin/admin-ajax.php?action=get_gare_calendario&d="

    print(f"--- 🚀 ACCESSO DIRETTO AI DATI: {url_sorgente} ---")
    
    try:
        res = requests.get(url_sorgente, headers=HEADERS, timeout=30)
        
        # Il sito restituisce un formato JSON (una lista di dati)
        gare_json = res.json()
        
        print(f"--- 📦 GARE RICEVUTE: {len(gare_json)} ---")

        batch_gare = []
        for gara in gare_json:
            # Estraiamo i dati utili dal JSON
            # Nota: i nomi dei campi nel JSON spesso sono diversi (es. 'id', 'titolo', 'data')
            if 'idComp' in gara:
                batch_gare.append({
                    "id_gara_fisi": str(gara.get('idComp')),
                    "gara_nome": gara.get('titolo_gara') or gara.get('nome'),
                    "localita": gara.get('localita'),
                    "data": gara.get('data_gara'),
                    "societa": gara.get('societa_organizzatrice')
                })

        if batch_gare:
            print(f"--- ✅ INVIO {len(batch_gare)} GARE A SUPABASE ---")
            supabase.table("gare").upsert(batch_gare).execute()
        else:
            print("--- ❌ Nessun dato trovato nel JSON. Verifico il contenuto... ---")
            print(f"DEBUG JSON: {str(gare_json)[:200]}")

    except Exception as e:
        print(f"--- 🔥 ERRORE: {e} ---")

if __name__ == "__main__":
    avvia_scraper_serio()
