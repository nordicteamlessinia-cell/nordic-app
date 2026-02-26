import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client

# Configurazione
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36'}

def avvia_scarico():
    comp_id = "56789" 
    url_base = f"https://comitati.fisi.org/veneto/competizione/?idComp={comp_id}&d="
    
    print(f"--- ANALISI COMPETIZIONE: {url_base} ---")
    res = requests.get(url_base, headers=HEADERS)
    soup = BeautifulSoup(res.text, 'html.parser')

    # Cerchiamo tutti i link (classifiche, ordini di partenza, etc)
    links = [l['href'] for l in soup.find_all('a', href=True)]
    
    # Filtriamo solo quelli che sembrano classifiche (idGara o link a file)
    gare_links = list(set([l for l in links if 'idGara=' in l]))

    for g_url in gare_links:
        full_url = g_url if g_url.startswith('http') else f"https://comitati.fisi.org/veneto/{g_url}"
        print(f"\n--- ANALIZZO CATEGORIA: {full_url} ---")
        
        res_g = requests.get(full_url, headers=HEADERS)
        g_soup = BeautifulSoup(res_g.text, 'html.parser')
        
        # DEBUG: Stampiamo i primi 500 caratteri della pagina per capire cosa c'è dentro
        print(f"DEBUG HTML: {res_g.text[:500]}")

        # Se non c'è tabella, cerchiamo link a PDF o file Excel
        file_links = [l['href'] for l in g_soup.find_all('a', href=True) if '.pdf' in l['href'].lower()]
        if file_links:
            print(f"   📂 Trovata classifica PDF: {file_links[0]}")
            # Qui servirebbe una libreria per leggere i PDF, ma iniziamo a vedere se li trova
            continue

        # Prova finale: cerchiamo testi che sembrano nomi di società veronesi
        testo_pagina = g_soup.get_text().upper()
        if "BOSCO" in testo_pagina or "VALILLASI" in testo_pagina:
            print("   ✅ Trovati riferimenti a club veronesi nel testo!")
