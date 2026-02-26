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
    comp_id = "56789" 
    url_gara = f"https://comitati.fisi.org/veneto/gara/?idGara=16299551&idComp={comp_id}&d="
    
    print(f"--- ANALISI PROFONDA GARA: {url_gara} ---")
    res = requests.get(url_gara, headers=HEADERS)
    soup = BeautifulSoup(res.text, 'html.parser')

    # 1. Vediamo se ci sono script o link nascosti
    links = soup.find_all('a', href=True)
    print(f"--- Link totali trovati: {len(links)}")
    
    for l in links:
        href = l['href']
        if ".pdf" in href.lower() or "classifica" in href.lower() or "download" in href.lower():
            print(f"--- 🎯 TROVATO POSSIBILE FILE: {href}")

    # 2. Vediamo se i dati sono "nascosti" nel testo della pagina
    testo = soup.get_text()
    if "Classifica" in testo or "Risultati" in testo:
        print("--- Parola 'Classifica' trovata nel testo, ma i dati sono invisibili.")
    else:
        print("--- La pagina sembra non contenere testo utile. Probabile caricamento dinamico.")

if __name__ == "__main__":
    avvia()
