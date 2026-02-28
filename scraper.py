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

def master_spider_atleti():
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
            
            id_sottogare = []
            for l in links:
                if 'idGara=' in l['href']:
                    id_g = l['href'].split('idGara=')[1].split('&')[0]
                    if id_g not in id_sottogare:
                        id_sottogare.append(id_g)
            
            if not id_sottogare:
                continue
            
            print(f"\n   🟢 Comp {id_comp}: Trovate {len(id_sottogare)} gare. Download atleti...")

            for id_g in id_sottogare:
                # 👉 LA VERA MODIFICA: Puntiamo direttamente alla pagina HTML della singola gara!
                url_singola_gara = f"https://comitati.fisi.org/veneto/gara/?idGara={id_g}&idComp={id_comp}&d=2025"
                r_data = requests.get(url_singola_gara, headers=HEADERS, timeout=15)
                
                classifica_soup = BeautifulSoup(r_data.text, 'html.parser')
                
                # Cerchiamo tutte le tabelle nella pagina
                tables = classifica_soup.find_all('table')
                
                if not tables:
                    print(f"      ⚠️ Gara {id_g}: Nessuna tabella HTML trovata nella pagina.")
                    continue

                batch_atleti = []
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows:
                        cols = row.find_all(['td', 'th'])
                        if len(cols) >= 5:
                            d = [c.get_text(strip=True) for c in cols]
                            # Se la prima cella contiene un numero (la Posizione in classifica)
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
                        print(f"      ✅ Gara {id_g}: {len(batch_atleti)} atleti salvati!")
                    except Exception as db_err:
                        print(f"      ❌ Errore DB: {db_err}")
                else:
                    print(f"      ⚠️ Gara {id_g}: Tabella presente, ma struttura non riconosciuta (nomi atleti non trovati).")
                
                time.sleep(0.5) # Pausa di sicurezza per non affaticare il server

        except Exception as e:
            print(f"   ❌ Errore sulla Comp {id_comp}: {e}")

if __name__ == "__main__":
    master_spider_atleti()
