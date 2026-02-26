import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client

# 1. Recupero credenziali dai Secrets di GitHub
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Inizializzazione client Supabase
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Errore: SUPABASE_URL o SUPABASE_KEY non trovati nei Secrets di GitHub")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Header per simulare un browser ed evitare blocchi dal sito FISI
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def avvia_scarico():
    # ID della competizione (Campionati Regionali Bosco Chiesanuova)
    comp_id = "56789" 
    url_competizione = f"https://comitati.fisi.org/veneto/competizione/?idComp={comp_id}&d="
    
    print(f"--- 1. Analizzo la competizione: {url_competizione} ---")
    
    try:
        res = requests.get(url_competizione, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')

        # Cerchiamo i link alle singole classifiche (idGara)
        links = [l['href'] for l in soup.find_all('a', href=True) if 'idGara=' in l['href']]
        links = list(set(links)) # Rimuove i duplicati
        
        print(f"--- 2. Gare (classifiche) trovate: {len(links)} ---")

        if not links:
            print("❌ Nessuna gara trovata. Verifica l'ID competizione o la struttura del sito.")
            return

        for g_url in links:
            # Gestione URL parziali/completi
            full_url = g_url if g_url.startswith('http') else f"https://comitati.fisi.org/veneto/{g_url}"
            id_fisi = full_url.split('idGara=')[1].split('&')[0]
            
            print(f"--- 3. Analizzo dettagli gara: {full_url} ---")
            res_g = requests.get(full_url, headers=HEADERS, timeout=20)
            g_soup = BeautifulSoup(res_g.text, 'html.parser')
            
            # Titolo della gara (es. U14 Ragazzi)
            titolo_gara = g_soup.find('h1').text.strip() if g_soup.find('h1') else "Gara Veneto"

            # Cerchiamo le righe della tabella risultati
            rows = g_soup.find_all('tr')
            batch_atleti = []

            for row in rows:
                cols = row.find_all(['td', 'th'])
                data = [c.get_text(strip=True) for c in cols]
                
                # Debug: stampa le righe per vedere la struttura nei log di GitHub
                if len(data) > 3:
                    print(f"   Dati riga: {data}")

                # La riga è valida se la prima o seconda colonna è un numero (Posizione)
                pos = None
                for potential_pos in data[:2]:
                    if potential_pos.isdigit():
                        pos =
