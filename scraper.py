import os
import requests
import json
from supabase import create_client

# 1. Configurazione Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 2. Configurazione API FISI Veneto
# L'azione corretta per il calendario è 'get_gare_calendario'
API_URL = "https://comitati.fisi.org/veneto/wp-admin/admin-ajax.php"
PARAMS = {
    'action': 'get_gare_calendario',
    'd': '2025'  # Stagione 2024/2025
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest',
    'Referer': 'https://comitati.fisi.org/veneto/calendario/'
}

def indagine_api():
    print(f"--- 🚀 CHIAMATA API DIRETTA: {API_URL} ---")
    
    try:
        # Effettuiamo la richiesta POST (spesso admin-ajax preferisce POST)
        response = requests.post(API_URL, data=PARAMS, headers=HEADERS, timeout=30)
        
        # Se la risposta è '0', WordPress non ha riconosciuto l'azione
        if response.text == '0':
            print("--- ❌ Errore: Il server ha risposto '0'. L'azione API potrebbe essere diversa. ---")
            return

        # Proviamo a decodificare il JSON
        try:
            gare = response.json()
        except Exception:
            print(f"--- ⚠️ Risposta non JSON. Anteprima: {response.text[:200]} ---")
            return

        print(f"--- ✅ DATI RICEVUTI: {len(gare)} elementi trovati ---")

        batch_gare = []
        for g in gare:
            # Mappiamo i campi del JSON ai campi della tua tabella Supabase
            # Nota: idComp è l'ID della competizione generale
            if g.get('idComp'):
                batch_gare.append({
                    "id_gara_fisi": str(g.get('idComp')),
                    "gara_nome": g.get('titolo_gara', 'N.D.'),
                    "localita": g.get('localita', 'N.D.'),
                    "data": g.get('data_gara', 'N.D.'),
                    "societa": g.get('societa_organizzatrice', 'N.D.')
                })

        if batch_gare:
            print(f"--- 💾 INVIO A SUPABASE: {len(batch_gare)} gare ---")
            # Assicurati che la tabella si chiami 'Gare' (o 'gare')
            supabase.table("Gare").upsert(batch_gare).execute()
            print("--- 🏁 OPERAZIONE COMPLETATA CON SUCCESSO ---")

    except Exception as e:
        print(f"--- 🔥 ERRORE CRITICO: {e} ---")

if __name__ == "__main__":
    indagine_api()
