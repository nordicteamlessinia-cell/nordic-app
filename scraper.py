import os
import requests
import re
from bs4 import BeautifulSoup
from supabase import create_client

# 1. Configurazione Supabase
url_sb = os.environ.get("SUPABASE_URL")
key_sb = os.environ.get("SUPABASE_KEY")
supabase = create_client(url_sb, key_sb)

# Header per simulare un browser umano ed evitare blocchi
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest'
}

def avvia_scraper_completo():
    comp_id = "56789"
    url_comp = f"https://comitati.fisi.org/veneto/competizione/?idComp={comp_id}&d="
    
    print(f"--- 🎯 FASE 1: Recupero elenco gare da {url_comp} ---")
    
    try:
        res = requests.get(url_comp, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Troviamo tutti i link alle singole gare
        links = list(set([l['href'] for l in soup.find_all('a', href=True) if 'idGara=' in l['href']]))
        print(f"--- 📊 Gare identificate: {len(links)} ---")

        for g_url in links:
            # Pulizia URL
            full_url = g_url if g_url.startswith('http') else f"https://comitati.fisi.org/veneto/{g_url}"
            id_gara = full_url.split('idGara=')[1].split('&')[0]
            
            print(f"\n--- 🔍 FASE 2: Estrazione Classifica Gara {id_gara} ---")
            
            # Chiamata AJAX diretta alla classifica per bypassare il caricamento dinamico
            url_dati = f"https://comitati.fisi.org/veneto/wp-admin/admin-ajax.php?action=get_classifica&idGara={id_gara}"
            
            res_dati = requests.get(url_dati, headers=HEADERS, timeout=30)
            data_soup = BeautifulSoup(res_dati.text, 'html.parser')
            
            rows = data_soup.find_all('tr')
            atleti_batch = []
            
            for row in rows:
                cols = row.find_all(['td', 'th'])
                data = [c.get_text(strip=True) for c in cols]
                
                # Verifichiamo se la riga contiene un atleta (Posizione numerica in colonna 0)
                if len(data) >= 5 and data[0].isdigit():
                    atleti_batch.append({
                        "id_gara_fisi": id_gara,
                        "posizione": int(data[0]),
                        "atleta_nome": data[2], # Nome Atleta
                        "societa": data[4]      # Nome Società
                    })

            if atleti_batch:
                print(f"   ✅ Trovati {len(atleti_batch)} atleti. Invio a Supabase...")
                try:
                    # NOTA: La tabella deve chiamarsi 'Gare' (G maiuscola) 
                    # e
