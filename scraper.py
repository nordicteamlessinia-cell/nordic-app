import os
import requests
import time
from bs4 import BeautifulSoup
from supabase import create_client

# Configurazione
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'}
BASE_URL = "https://comitati.fisi.org/wp-admin/admin-ajax.php"

def master_spider_sicuro():
    print("--- 📂 Lettura competizioni dal database... ---")
    gare_db = supabase.table("Gare").select("id_gara_fisi").execute()
    id_competizioni = [g['id_gara_fisi'] for g in gare_db.data]
    
    print(f"--- 🕷️ Inizio scansione su {len(id_competizioni)} record ---")

    for id_comp in id_competizioni:
        # FILTRO DI SICUREZZA: Ignoriamo ID vuoti o ID delle vecchie sotto-gare (lunghi 8 cifre)
        if not id_comp or str(id_comp) == "None" or len(str(id_comp)) > 6:
            print(f"   ⏩ Salto record sporco/vecchio: {id_comp}")
            continue

        url_comp = f"https://comitati.fisi.org/veneto/competizione/?idComp={id_comp}&d=2025"
        
        try:
            res = requests.get(url_comp, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            links = soup.find_all('a', href=True)
            
            id_sottogare = []
            for l in links:
                if 'idGara=' in l['href']:
                    id_g = l['href'].split('idGara=')[1].split('&')[0]
                    if id_g not in id_sottogare:
                        id_sottogare.append(id_g)
            
            if not id_sottogare:
                print(f"   🟡 Comp {id_comp}: Nessuna sottogara trovata.")
                continue
            
            print(f"\n   🟢 Comp {id_comp}: Trovate {len(id_sottogare)} sottogare. Download atleti...")

            for id_g in id_sottogare:
                params = {"action": "get_classifica", "idGara": id_g}
                r_data = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=15)
                
                if r_data.text == "0" or len(r_data.text) < 100:
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
                    try:
                        supabase.table("Risultati").upsert(batch_atleti).execute()
                        print(f"      ✅ Gara {id_g}: {len(batch_atleti)} atleti salvati")
                    except Exception as db_err:
                        print(f"      ❌ Errore DB: {db_err}")
                
                time.sleep(0.5)

        except Exception as e:
            print(f"   ❌ Errore sulla Comp {id_comp}: {e}")

if __name__ == "__main__":
    master_spider_sicuro()
