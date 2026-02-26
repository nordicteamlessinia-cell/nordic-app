import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client

# 1. Recupero credenziali
url_sb = os.environ.get("SUPABASE_URL")
key_sb = os.environ.get("SUPABASE_KEY")

print(f"--- DEBUG: SUPABASE_URL presente: {bool(url_sb)}")
print(f"--- DEBUG: SUPABASE_KEY presente: {bool(key_sb)}")

supabase = create_client(url_sb, key_sb)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/110.0.0.0 Safari/537.36'}

def avvia():
    # TEST: Usiamo l'ID di una gara che sappiamo avere risultati (es. 56789)
    comp_id = "56789" 
    url = f"https://comitati.fisi.org/veneto/competizione/?idComp={comp_id}&d="
    
    print(f"--- 1. TENTATIVO DI CONNESSIONE A: {url}")
    
    try:
        res = requests.get(url, headers=HEADERS, timeout=30)
        print(f"--- 2. RISPOSTA SITO FISI: {res.status_code}")
        
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Cerchiamo i link idGara
        links = [l['href'] for l in soup.find_all('a', href=True) if 'idGara=' in l['href']]
        print(f"--- 3. LINK GARE TROVATI: {len(links)}")

        for g_url in list(set(links)):
            full_url = g_url if g_url.startswith('http') else f"https://comitati.fisi.org/veneto/{g_url}"
            print(f"--- 4. ANALIZZO GARA: {full_url}")
            
            res_g = requests.get(full_url, headers=HEADERS)
            g_soup = BeautifulSoup(res_g.text, 'html.parser')
            
            # Cerchiamo la tabella o i link PDF
            table = g_soup.find('table')
            if table:
                print("--- 5. TABELLA TROVATA! Estrazione dati...")
                # (Logica di estrazione qui...)
            else:
                # Se non c'è tabella, cerchiamo il PDF
                pdf = [l['href'] for l in g_soup.find_all('a', href=True) if '.pdf' in l['href'].lower()]
                if pdf:
                    print(f"--- 5. TROVATO PDF: {pdf[0]}")
                else:
                    print("--- 5. NESSUN DATO (Tabella o PDF) in questa pagina.")

    except Exception as e:
        print(f"--- ERRORE DURANTE L'ESECUZIONE: {e}")

if __name__ == "__main__":
    avvia()
