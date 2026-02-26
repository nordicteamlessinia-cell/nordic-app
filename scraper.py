import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client

# 1. Configurazione Supabase
url_sb = os.environ.get("SUPABASE_URL")
key_sb = os.environ.get("SUPABASE_KEY")
supabase = create_client(url_sb, key_sb)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}

def avvia_totale():
    comp_id = "56789"
    url_comp = f"https://comitati.fisi.org/veneto/competizione/?idComp={comp_id}&d="
    
    print(f"--- 🎯 FASE 1: Recupero elenco gare da {url_comp} ---")
    res = requests.get(url_comp, headers=HEADERS)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    # Troviamo i link unici delle gare
    links = list(set([l['href'] for l in soup.find_all('a', href=True) if 'idGara=' in l['href']]))
    print(f"--- 📊 Gare trovate: {len(links)} ---")

    for g_url in links:
        full_url = g_url if g_url.startswith('http') else f"https://comitati.fisi.org/veneto/{g_url}"
        id_gara = full_url.split('idGara=')[1].split('&')[0]
        
        print(f"\n--- 🔍 FASE 2: Analizzo Classifica Gara {id_gara} ---")
        
        res_g = requests.get(full_url, headers=HEADERS)
        g_soup = BeautifulSoup(res_g.text, 'html.parser')
        
        # Cerchiamo la tabella risultati
        rows = g_soup.find_all('tr')
        atleti_batch = []
        
        for row in rows:
            cols = row.find_all(['td', 'th'])
            data = [c.get_text(strip=True) for c in cols]
            
            # Se la riga ha una posizione numerica nella prima colonna, è un atleta
            if len(data) >= 5 and data[0].isdigit():
                atleti_batch.append({
                    "id_gara_fisi": id_gara,
                    "posizione": int(data[0]),
                    "atleta_nome": data[2],
                    "societa": data[4]
                })

        if atleti_batch:
            print(f"   ✅ Trovati {len(atleti_batch)} atleti. Invio a Supabase...")
            try:
                # Assicurati che la tabella su Supabase si chiami 'Gare' 
                # e abbia le colonne: id_gara_fisi, posizione, atleta_nome, societa
                supabase.table("Gare").upsert(atleti_batch).execute()
            except Exception as e:
                print(f"   ❌ Errore invio: {e}")
        else:
            print(f"   ⚠️ Nessun dato trovato nella tabella della gara {id_gara}")

    print("\n--- 🏁 SCRAPER COMPLETATO ---")

if __name__ == "__main__":
    avvia_totale()
