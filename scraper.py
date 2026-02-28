import os
import requests
import time
from bs4 import BeautifulSoup
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BASE_URL = "https://comitati.fisi.org/wp-admin/admin-ajax.php"

def test_cecchino_gara_invernale():
    # Puntiamo DRITTI alla gara invernale che sappiamo avere i dati
    id_comp = "56782"
    print(f"--- 🎯 TEST DIRETTO SULLA GARA INVERNALE ({id_comp}) ---")
    
    url_comp = f"https://comitati.fisi.org/veneto/competizione/?idComp={id_comp}&d=2025"
    HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'}
    
    try:
        res = requests.get(url_comp, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        links = soup.find_all('a', href=True)
        
        id_sottogare = list(set([l['href'].split('idGara=')[1].split('&')[0] for l in links if 'idGara=' in l['href']]))
        print(f"\n🟢 Comp {id_comp}: Trovate {len(id_sottogare)} gare invernali. Inizio estrazione...")

        for id_g in id_sottogare:
            # 🛡️ PROTEZIONE EXTRA: Diciamo al server da quale pagina stiamo facendo la richiesta
            headers_ajax = HEADERS.copy()
            headers_ajax['Referer'] = f"https://comitati.fisi.org/veneto/gara/?idGara={id_g}&idComp={id_comp}&d=2025"
            headers_ajax['X-Requested-With'] = 'XMLHttpRequest'

            params = {
                "action": "get_classifica", 
                "idGara": id_g,
                "d": "2025"
            }
            
            r_data = requests.get(BASE_URL, params=params, headers=headers_ajax, timeout=15)
            
            if r_data.text == "0" or len(r_data.text.strip()) < 100:
                print(f"   ⏩ Gara {id_g}: Nessun risultato (Server risponde vuoto)")
                continue

            classifica_soup = BeautifulSoup(r_data.text, 'html.parser')
            rows = classifica_soup.find_all('tr')
            batch_atleti = []
            
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 5:
                    d = [c.get_text(strip=True) for c in cols]
                    if d[0].isdigit():
                        batch_atleti.append({
                            "id_gara_fisi": id_g, 
                            "posizione": int(d[0]),
                            "atleta_nome": d[2],
                            "societa": d[4]
                        })
            
            if batch_atleti:
                print(f"   ✅ Gara {id_g}: {len(batch_atleti)} ATLETI TROVATI E SALVATI SU SUPABASE!")
                supabase.table("Risultati").upsert(batch_atleti).execute()
            else:
                print(f"   ⚠️ Gara {id_g}: Pagina caricata, ma struttura tabella non standard.")
            
            time.sleep(0.5)

    except Exception as e:
        print(f"❌ Errore critico: {e}")

if __name__ == "__main__":
    test_cecchino_gara_invernale()
