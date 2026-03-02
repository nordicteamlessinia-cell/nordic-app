import os
import requests
import time
from bs4 import BeautifulSoup
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'}

def calcola_stagione_fisi(data_gara):
    """Calcola l'ID della stagione FISI partendo dalla data (es. 15/12/2023 -> 2024)"""
    try:
        if not data_gara or data_gara == "N/D":
            return "2026" # Fallback sull'anno corrente
            
        # Assumiamo formato DD/MM/YYYY
        parti = data_gara.split("/")
        if len(parti) == 3:
            mese = int(parti[1])
            anno = int(parti[2])
            # Se la gara è da giugno in poi, fa parte della stagione invernale dell'anno dopo
            if mese >= 6:
                return str(anno + 1)
            else:
                return str(anno)
    except Exception:
        pass
    return "2026"

def spider_storico_totale():
    print("--- 📂 RECUPERO GARE DAL DATABASE... ---")
    # Peschiamo non solo l'ID, ma anche la data per calcolare la stagione!
    gare_db = supabase.table("Gare").select("id_gara_fisi, data_gara, gara_nome").execute()
    lista_gare = gare_db.data

    print(f"--- 🕷️ INIZIO SCANSIONE SU {len(lista_gare)} EVENTI STORICI ---")

    for gara in lista_gare:
        id_comp = gara.get('id_gara_fisi')
        data_g = gara.get('data_gara')
        nome_g = gara.get('gara_nome')
        
        if not id_comp: continue
        
        stagione_fisi = calcola_stagione_fisi(data_g)
        print(f"\n🟢 Analizzo: {nome_g} (Data: {data_g} -> Stagione FISI: {stagione_fisi})")
        
        url_comp = f"https://comitati.fisi.org/veneto/competizione/?idComp={id_comp}&d={stagione_fisi}"
        
        try:
            res = requests.get(url_comp, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            links = soup.find_all('a', href=True)
            id_sottogare = list(set([l['href'].split('idGara=')[1].split('&')[0] for l in links if 'idGara=' in l['href']]))
            
            if not id_sottogare:
                print("   ⏩ Nessuna sottogara trovata. Salto.")
                continue

            for id_g in id_sottogare:
                url_gara = f"https://comitati.fisi.org/veneto/gara/?idGara={id_g}&idComp={id_comp}&d={stagione_fisi}"
                r_data = requests.get(url_gara, headers=HEADERS, timeout=15)
                gara_soup = BeautifulSoup(r_data.text, 'html.parser')
                
                testi_pagina = [e.get_text(strip=True) for e in gara_soup.find_all('span', class_='x-text-content-text-primary') if e.get_text(strip=True)]
                
                # 🎯 CERCATORE DI CATEGORIA INFALLIBILE
                categoria_trovata = "Generale"
                for i, t in enumerate(testi_pagina[:60]):
                    if t.upper() == "CATEGORIA":
                        categoria_trovata = testi_pagina[i+1]
                        break

                batch_atleti = []
                i = 0
                while i < len(testi_pagina) - 7:
                    if testi_pagina[i].isdigit() and testi_pagina[i+1].isdigit() and len(testi_pagina[i+1]) >= 3:
                        batch_atleti.append({
                            "id_gara_fisi": id_g, 
                            "id_comp_collegata": id_comp, 
                            "posizione": int(testi_pagina[i]),
                            "atleta_nome": testi_pagina[i+2],
                            "societa": testi_pagina[i+4],
                            "categoria": categoria_trovata 
                        })
                        i += 8
                    else:
                        i += 1
                
                if batch_atleti:
                    # L'Upsert ci protegge dai duplicati se lo lanciamo più volte
                    supabase.table("Risultati").upsert(batch_atleti).execute()
                    print(f"   ✅ Gara {id_g}: {len(batch_atleti)} atleti salvati in [{categoria_trovata}]")
                
                time.sleep(0.5) # Pausa di sicurezza per non bloccare il server

        except Exception as e:
            print(f"   ❌ Errore sull'evento {id_comp}: {e}")

if __name__ == "__main__":
    spider_storico_totale()
