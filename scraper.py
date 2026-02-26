import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client

# Configurazione con check immediato
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36'}

def avvia_scraper():
    print("--- 1. Inizio Scraper ---")
    # Usiamo l'ID che abbiamo visto prima (Campionati Regionali Bosco)
    comp_id = "56789" 
    url_fisi = f"https://comitati.fisi.org/veneto/competizione/?idComp={comp_id}&d="
    
    print(f"--- 2. Cerco gare su: {url_fisi}")
    res = requests.get(url_fisi, headers=HEADERS)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    # Cerchiamo i link idGara
    links = [l['href'] for l in soup.find_all('a', href=True) if 'idGara=' in l['href']]
    links = list(set(links))
    
    print(f"--- 3. Gare trovate: {len(links)}")
    
    if len(links) == 0:
        print("❌ Nessun link gara trovato. Probabile cambio struttura sito FISI.")
        # Debug: stampiamo un pezzetto di HTML per capire cosa vede il bot
        print(res.text[:500]) 
        return

    for g_url in links:
        print(f"--- 4. Analizzo gara: {g_url}")
        res_g = requests.get(g_url, headers=HEADERS)
        g_soup = BeautifulSoup(res_g.text, 'html.parser')
        
        table = g_soup.find('table')
        if not table:
            print("   ❌ Tabella non trovata in questa pagina.")
            continue
            
        rows = table.find_all('tr')[1:] # Salta intestazione
        atleti = []
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 5:
                atleti.append({
                    "atleta_nome": cols[2].text.strip(),
                    "societa": cols[4].text.strip(),
                    "posizione": int(cols[0].text.strip()) if cols[0].text.strip().isdigit() else 0,
                    "id_gara_fisi": g_url.split('idGara=')[1].split('&')[0]
                })
        
        if atleti:
            print(f"   ✅ Trovati {len(atleti)} atleti. Provo a inviare a Supabase...")
            result = supabase.table("gare").upsert(atleti).execute()
            print(f"   🚀 Risposta Database: {result}")

if __name__ == "__main__":
    avvia_scraper()
