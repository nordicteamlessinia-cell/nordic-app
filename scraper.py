import os
import requests
import re
import json
from supabase import create_client

# 1. Configurazione Supabase
url_sb = os.environ.get("SUPABASE_URL")
key_sb = os.environ.get("SUPABASE_KEY")
supabase = create_client(url_sb, key_sb)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
}

def avvia_scraper_definitivo():
    # Puntiamo alla pagina del calendario 2024/2025
    url = "https://comitati.fisi.org/veneto/calendario/?d=2025"
    
    print(f"--- 🚀 ANALISI PAGINA CALENDARIO: {url} ---")
    
    try:
        res = requests.get(url, headers=HEADERS, timeout=30)
        content = res.text
        
        # 2. CERCHIAMO I DATI NASCOSTI NEL JAVASCRIPT
        # Il sito spesso salva i dati in una variabile chiamata 'data' o simile dentro un tag <script>
        # Proviamo a estrarre tutto ciò che somiglia a un array di gare
        print("--- 🔍 Ricerca pattern dati nel codice sorgente... ---")
        
        # Cerchiamo blocchi di testo che contengono "idComp" e sembrano JSON
        matches = re.findall(r'\{"idComp":.*?\}(?=\s*[,\]])', content)
        
        if not matches:
            # Se non troviamo JSON pronti, cerchiamo i link diretti alle gare nell'HTML
            print("--- ⚠️ Nessun JSON trovato. Cerco link diretti alle gare... ---")
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')
            links = [l['href'] for l in soup.find_all('a', href=True) if 'idComp=' in l['href']]
            matches = list(set(links))

        if matches:
            print(f"--- 📦 ELEMENTI TROVATI: {len(matches)} ---")
            batch = []
            for item in matches[:50]: # Proviamo i primi 50 per test
                # Se è un JSON, lo puliamo e lo carichiamo
                if item.startswith('{'):
                    try:
                        g = json.loads(item)
                        batch.append({
                            "id_gara_fisi": str(g.get('idComp', '')),
                            "gara_nome": g.get('titolo_gara', 'Gara'),
                            "localita": g.get('localita', ''),
                            "data": g.get('data_gara', '')
                        })
                    except:
                        continue
                else:
                    # Se è un link, estraiamo l'ID
                    match_id = re.search(r'idComp=(\d+)', item)
                    if match_id:
                        batch.append({
                            "id_gara_fisi": match_id.group(1),
                            "gara_nome": "Gara da link",
                            "data": "2025"
                        })

            if batch:
                print(f"--- ✅ INVIO {len(batch)} RIGHE A SUPABASE ---")
                supabase.table("gare").upsert(batch).execute()
            else:
                print("--- ❌ Nessun dato utile estratto dai match. ---")
        else:
            print("--- ❌ La pagina sembra vuota o protetta. ---")
            print(f"DEBUG CONTENUTO (primi 200 car.): {content[:200]}")

    except Exception as e:
        print(f"--- 🔥 ERRORE: {e} ---")

if __name__ == "__main__":
    avvia_scraper_definitivo()
