import os
import requests
import time
from bs4 import BeautifulSoup
from supabase import create_client

# Configurazione
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}
BASE_URL = "https://comitati.fisi.org/wp-admin/admin-ajax.php"

def master_spider():
    # 1. Recuperiamo tutte le competizioni che abbiamo nel calendario
    print("--- 📂 Lettura competizioni dal database... ---")
    gare_db = supabase.table("Gare").select("id_gara_fisi").execute()
    id_competizioni = [g['id_gara_fisi'] for g in gare_db.data]
    
    print(f"--- 🕷️ Inizio scansione profonda su {len(id_competizioni)} competizioni ---")

    for id_comp in id_competizioni:
        url_comp = f"https://comitati.fisi.org/veneto/competizione/?idComp={id_comp}&d="
        
        try:
            # Step A: Entriamo nella competizione per trovare le singole gare (idGara)
            res = requests.get(url_comp, headers=HEADERS, timeout=20)
            soup = BeautifulSoup(res.text, 'html.parser')
            links = soup.find_all('a', href=True)
            
            # Estraiamo gli ID univoci delle sottogare (idGara)
            id_sottogare = list(set([l['href'].split('idGara=')[1].split('&')[0] for l in links if 'idGara=' in l['href']]))
            
            if not id_sottogare:
                print(f"   🟡 Comp {id_comp}: Nessuna sottogara trovata (forse futura).")
                continue

            for id_g in id_sottogare:
                # Step B: Chiamata AJAX per i risultati della singola gara
                print(f"      🔍 Scarico risultati gara {id_g}...", end=" ")
                params = {"action": "get_classifica", "idGara": id_g}
                r_data = requests.get(BASE_URL, params=params, headers=HEADERS)
                
                if r_data.text == "0" or len(r_data.text) < 100:
                    print("Vuota.")
                    continue

                # Step C: Parsing della tabella risultati
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
                                "id_competizione_padre": id_comp, # Utile per i filtri
                                "posizione": int(d[0]),
                                "atleta_nome": d[2],
                                "societa": d[4]
                            })
                
                if batch_atleti:
                    # Step D: Invio massivo a Supabase
                    supabase.table("Risultati").upsert(batch_atleti).execute()
                    print(f"✅ ({len(batch_atleti)} atleti salvati)")
                
                # Pausa etica per non farsi bannare l'IP
                time.sleep(0.5)

        except Exception as e:
            print(f"\n   ❌ Errore critico su Comp {id_comp}: {e}")
            continue

if __name__ == "__main__":
    master_spider()
