import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client

# Configurazione standard
url_sb = os.environ.get("SUPABASE_URL")
key_sb = os.environ.get("SUPABASE_KEY")
supabase = create_client(url_sb, key_sb)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}

def avvia():
    # 1. Ripartiamo dalla pagina che funzionava (ID Competizione)
    comp_id = "56789"
    url_target = f"https://comitati.fisi.org/veneto/competizione/?idComp={comp_id}&d="
    
    print(f"--- 🎯 RIPARTIAMO DA: {url_target} ---")
    
    res = requests.get(url_target, headers=HEADERS)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    # Recuperiamo i link delle 12 gare (questo funzionava!)
    links = list(set([l['href'] for l in soup.find_all('a', href=True) if 'idGara=' in l['href']]))
    print(f"--- 📊 GARE TROVATE: {len(links)} ---")

    for g_url in links[:2]: # Proviamo solo le prime 2 per non fare confusione
        full_url = g_url if g_url.startswith('http') else f"https://comitati.fisi.org/veneto/{g_url}"
        print(f"\n--- 🔍 ISPEZIONE GARA: {full_url} ---")
        
        res_g = requests.get(full_url, headers=HEADERS)
        g_soup = BeautifulSoup(res_g.text, 'html.parser')
        
        # PROVA A: Cerca tabelle standard
        table = g_soup.find('table')
        if table:
            print("   ✅ TABELLA TROVATA! Provo a leggere le righe...")
            # ... logica estrazione ...
        else:
            # PROVA B: Se non c'è tabella, stampa il TESTO della pagina
            # Questo ci dirà se i nomi sono lì ma non in una tabella
            testo_pulito = g_soup.get_text(separator=' ', strip=True)
            print(f"   📄 ANTEPRIMA TESTO PAGINA: {testo_pulito[:300]}...")
            
            # PROVA C: Cerca link a PDF (MOLTO PROBABILE)
            pdf = [l['href'] for l in g_soup.find_all('a', href=True) if '.pdf' in l['href'].lower()]
            if pdf:
                print(f"   🎯 TROVATO PDF CLASSIFICA: {pdf[0]}")

if __name__ == "__main__":
    avvia()
