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
    url = f"https://comitati.fisi.org/veneto/competizione/?idComp={comp_id}&d="
    
    print(f"--- 🎯 TARGET: {url} ---")
    
    res = requests.get(url, headers=HEADERS, timeout=30)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    links = soup.find_all('a', href=True)
    gare_trovate = []
    
    for l in links:
        href = l['href']
        if 'idGara=' in href:
            full_url = href if href.startswith('http') else f"https://comitati.fisi.org/veneto/{href}"
            gare_trovate.append(full_url)
            
    print(f"--- 📊 GARE IDENTIFICATE: {len(gare_trovate)} ---")
    
    if gare_trovate:
        batch = []
        # Prendiamo gli ID unici
        set_gare = list(set(gare_trovate))
        
        for g in set_gare:
            id_gara = g.split('idGara=')[1].split('&')[0]
            # Inviamo solo le colonne che siamo SICURI esistano
            # Se la tua tabella ha nomi diversi, modificali qui sotto
            batch.append({
                "id_gara_fisi": id_gara,
                "gara_nome": f"Gara ID {id_gara}"
            })

        print(f"--- 🚀 INVIO A DATABASE (Tabella: Gare) ---")
        try:
            # Prova a usare "Gare" (G maiuscola) o "gare" in base al test precedente
            # Se l'errore prima diceva "Perhaps you meant Gare", usa "Gare"
            supabase.table("Gare").upsert(batch).execute()
            print("--- ✅ OPERAZIONE COMPLETATA! Controlla Supabase. ---")
        except Exception as e:
            print(f"--- ❌ ERRORE: {e} ---")
            print("Se l'errore dice ancora 'Could not find column', controlla i nomi delle colonne su Supabase.")
    else:
        print("--- ❌ Nessuna gara trovata. ---")

if __name__ == "__main__":
    avvia()
