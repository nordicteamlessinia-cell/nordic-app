import os
import requests
from supabase import create_client

# 1. Configurazione Supabase
url_sb = os.environ.get("SUPABASE_URL")
key_sb = os.environ.get("SUPABASE_KEY")
supabase = create_client(url_sb, key_sb)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest'
}

def avvia_scraper_serio():
    # Aggiungiamo il parametro della stagione (es. 2024 per 2023/24 o 2025)
    # Il sito FISI spesso vuole sapere l'anno specifico
    url_sorgente = "https://comitati.fisi.org/veneto/wp-admin/admin-ajax.php"
    params = {
        'action': 'get_gare_calendario',
        'd': '2025' # Prova con 2024 se non vedi risultati
    }

    print(f"--- 🚀 TENTATIVO DI ACCESSO AI DATI 2025 ---")
    
    try:
        res = requests.get(url_sorgente, params=params, headers=HEADERS, timeout=30)
        
        # Verifichiamo cosa ci ha risposto davvero il server
        print(f"DEBUG RISPOSTA: {res.text[:100]}")
        
        # Se la risposta è '0' o un numero, il sito ci sta rimbalzando
        if res.text.strip() == '0' or not res.text.strip():
            print("--- ❌ Il server ha risposto '0'. Parametri errati o sessione scaduta. ---")
            return

        gare_json = res.json()
        
        # Controllo di sicurezza: verifichiamo se è una lista
        if isinstance(gare_json, list):
            print(f"--- 📦 GARE RICEVUTE: {len(gare_json)} ---")
            
            batch_gare = []
            for gara in gare_json:
                if isinstance(gara, dict):
                    batch_gare.append({
                        "id_gara_fisi": str(gara.get('idComp', '')),
                        "gara_nome": gara.get('titolo_gara', 'Gara senza nome'),
                        "localita": gara.get('localita', ''),
                        "data": gara.get('data_gara', ''),
                        "societa": gara.get('societa_organizzatrice', '')
                    })

            if batch_gare:
                print(f"--- ✅ INVIO {len(batch_gare)} GARE A SUPABASE ---")
                supabase.table("gare").upsert(batch_gare).execute()
        else:
            print(f"--- ⚠️ Formato inaspettato: {type(gare_json)} ---")

    except Exception as e:
        print(f"--- 🔥 ERRORE: {e} ---")

if __name__ == "__main__":
    avvia_scraper_serio()
