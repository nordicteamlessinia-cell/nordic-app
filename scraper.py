import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client

# Configurazione
url_sb = os.environ.get("SUPABASE_URL")
key_sb = os.environ.get("SUPABASE_KEY")
supabase = create_client(url_sb, key_sb)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}

def avvia():
    # Usiamo l'ID competizione che avevi postato all'inizio
    comp_id = "56789"
    url = f"https://comitati.fisi.org/veneto/competizione/?idComp={comp_id}&d="
    
    print(f"--- 🎯 TARGET: {url} ---")
    
    res = requests.get(url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    # Cerchiamo tutti i link che portano a una gara specifica
    # Questi link sono solitamente statici e leggibili
    links = soup.find_all('a', href=True)
    gare_trovate = []
    
    for l in links:
        href = l['href']
        if 'idGara=' in href:
            # Puliamo l'URL
            full_url = href if href.startswith('http') else f"https://comitati.fisi.org/veneto/{href}"
            gare_trovate.append(full_url)
            
    print(f"--- 📊 GARE IDENTIFICATE NELLA PAGINA: {len(gare_trovate)} ---")
    
    if gare_trovate:
        batch = []
        for g in list(set(gare_trovate)): # Rimuove duplicati
            id_gara = g.split('idGara=')[1].split('&')[0]
            batch.append({
                "id_gara_fisi": id_gara,
                "gara_nome": f"Gara ID {id_gara}",
                "localita": "Velo Veronese / Bosco",
                "data": "2024/2025"
            })
            print(f"   > Rilevata Gara: {id_gara}")

        # Invio a Supabase
        print(f"--- 🚀 INVIO A DATABASE... ---")
        supabase.table("gare").upsert(batch).execute()
        print("--- ✅ OPERAZIONE COMPLETATA ---")
    else:
        print("--- ❌ Nessuna gara trovata. Stampo HTML per capire cosa vede il bot: ---")
        print(res.text[:500])

if __name__ == "__main__":
    avvia()
