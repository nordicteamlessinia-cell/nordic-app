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

def spider_definitivo():
    print("--- 📂 Lettura competizioni dal database... ---")
    gare_db = supabase.table("Gare").select("id_gara_fisi").execute()
    id_competizioni = [g['id_gara_fisi'] for g in gare_db.data]
    
    print(f"--- 🕷️ Inizio scansione su {len(id_competizioni)} competizioni ---")

    for id_comp in id_competizioni:
        if not id_comp or str(id_comp) == "None":
            continue

        url_comp = f"https://comitati.fisi.org/veneto/competizione/?idComp={id_comp}&d=2025"
        
        try:
            res = requests.get(url_comp, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            links = soup.find_all('a', href=True)
            
            id_sottogare = list(set([l['href'].split('idGara=')[1].split('&')[0] for l in links if 'idGara=' in l['href']]))
            
            if not id_sottogare:
                continue
            
            print(f"\n🟢 Comp {id_comp}: Trovate {len(id_sottogare)} gare. Estrazione in corso...")

            for id_g in id_sottogare:
                url_gara = f"https://comitati.fisi.org/veneto/gara/?idGara={id_g}&idComp={id_comp}&d=2025"
                r_data = requests.get(url_gara, headers=HEADERS, timeout=15)
                gara_soup = BeautifulSoup(r_data.text, 'html.parser')
                
                # Il trucco magico: peschiamo solo dalle scatole invisibili del sito
                elementi = gara_soup.find_all('span', class_='x-text-content-text-primary')
                testi = [e.get_text(strip=True) for e in elementi if len(e.get_text(strip=True)) > 0]
                
                batch_atleti = []
                i = 0
                
                # Algoritmo "Finestra Scorrevole": cerchiamo Posizione (numero) + Cod. FISI (numero lungo)
                while i < len(testi) - 7:
                    if testi[i].isdigit() and testi[i+1].isdigit() and len(testi[i+1]) >= 3:
                        batch_atleti.append({
                            "id_gara_fisi": id_g, 
                            "posizione": int(testi[i]),
                            "atleta_nome": testi[i+2],
                            "societa": testi[i+4]
                        })
                        i += 8 # Saltiamo al blocco del prossimo atleta!
                    else:
                        i += 1 # Saltiamo le intestazioni e i menu
                
                if batch_atleti:
                    try:
                        supabase.table("Risultati").upsert(batch_atleti).execute()
                        print(f"   ✅ Gara {id_g}: {len(batch_atleti)} atleti salvati su Supabase!")
                    except Exception as db_err:
                        print(f"   ❌ Errore DB su Gara {id_g}: {db_err}")
                else:
                    print(f"   ⏩ Gara {id_g}: Nessuna classifica presente.")
                
                time.sleep(0.5) # Pausa di cortesia per non far arrabbiare il server

        except Exception as e:
            print(f"❌ Errore sulla Comp {id_comp}: {e}")

if __name__ == "__main__":
    spider_definitivo()
