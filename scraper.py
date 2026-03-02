import os
import requests
import time
from bs4 import BeautifulSoup
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def spider_con_categorie():
    gare_db = supabase.table("Gare").select("id_gara_fisi").execute()
    id_competizioni = [g['id_gara_fisi'] for g in gare_db.data]

    for id_comp in id_competizioni:
        if not id_comp: continue
        url_comp = f"https://comitati.fisi.org/veneto/competizione/?idComp={id_comp}&d=2026"
        
        try:
            res = requests.get(url_comp, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            links = soup.find_all('a', href=True)
            id_sottogare = list(set([l['href'].split('idGara=')[1].split('&')[0] for l in links if 'idGara=' in l['href']]))
            
            for id_g in id_sottogare:
                url_gara = f"https://comitati.fisi.org/veneto/gara/?idGara={id_g}&idComp={id_comp}&d=2026"
                r_data = requests.get(url_gara, headers=HEADERS, timeout=15)
                gara_soup = BeautifulSoup(r_data.text, 'html.parser')
                
                # CATTURIAMO LA CATEGORIA (Solitamente è nei titoli principali della pagina)
                # Estraiamo un po' di testi iniziali per trovare la categoria (es. Slalom, U16)
                testi_pagina = [e.get_text(strip=True) for e in gara_soup.find_all('span', class_='x-text-content-text-primary') if e.get_text(strip=True)]
                
                categoria_trovata = "Generale"
                for i, t in enumerate(testi_pagina[:40]): 
                    # Cerchiamo parole chiave tipiche delle categorie FISI
                    if " MASCHILE" in t.upper() or " FEMMINILE" in t.upper() or "U14" in t.upper() or "U16" in t.upper() or "GIOVANI" in t.upper():
                        categoria_trovata = t
                        break

                batch_atleti = []
                i = 0
                while i < len(testi_pagina) - 7:
                    if testi_pagina[i].isdigit() and testi_pagina[i+1].isdigit() and len(testi_pagina[i+1]) >= 3:
                        batch_atleti.append({
                            "id_gara_fisi": id_g, 
                            "id_comp_collegata": id_comp, # NUOVO! Per unire i database
                            "posizione": int(testi_pagina[i]),
                            "atleta_nome": testi_pagina[i+2],
                            "societa": testi_pagina[i+4],
                            "categoria": categoria_trovata # NUOVO!
                        })
                        i += 8
                    else:
                        i += 1
                
                if batch_atleti:
                    supabase.table("Risultati").upsert(batch_atleti).execute()
                    print(f"✅ Gara {id_g}: {len(batch_atleti)} atleti salvati in {categoria_trovata}!")
                
                time.sleep(0.5)

        except Exception as e:
            print(f"❌ Errore: {e}")

if __name__ == "__main__":
    spider_con_categorie()
