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
    try:
        if not data_gara or data_gara == "N/D": return "2026"
        p = data_gara.split("/")
        if len(p) == 3:
            return str(int(p[2]) + 1) if int(p[1]) >= 6 else str(p[2])
    except: pass
    return "2026"

def spider_definitivo_con_specialita():
    print("--- 📂 RECUPERO GARE DAL DATABASE... ---")
    gare_db = supabase.table("Gare").select("id_gara_fisi, data_gara, gara_nome").execute()
    lista_gare = gare_db.data

    print(f"--- 🕷️ INIZIO SCANSIONE STORICA CON CATEGORIE FUSE ---")

    for gara in lista_gare:
        id_comp = gara.get('id_gara_fisi')
        data_g = gara.get('data_gara')
        
        if not id_comp: continue
        stagione_fisi = calcola_stagione_fisi(data_g)
        
        url_comp = f"https://comitati.fisi.org/veneto/competizione/?idComp={id_comp}&d={stagione_fisi}"
        
        try:
            res = requests.get(url_comp, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            links = soup.find_all('a', href=True)
            id_sottogare = list(set([l['href'].split('idGara=')[1].split('&')[0] for l in links if 'idGara=' in l['href']]))
            
            for id_g in id_sottogare:
                url_gara = f"https://comitati.fisi.org/veneto/gara/?idGara={id_g}&idComp={id_comp}&d={stagione_fisi}"
                r_data = requests.get(url_gara, headers=HEADERS, timeout=15)
                gara_soup = BeautifulSoup(r_data.text, 'html.parser')
                
                # 🎯 1. FASE INTESTAZIONE: Estraiamo TUTTO il testo puro per trovare Specialità e Categoria reali
                testi_completi = list(gara_soup.stripped_strings)
                cat = ""
                spec = ""
                
                for i, t in enumerate(testi_completi):
                    testo_upper = t.upper()
                    # Cerchiamo la parola e prendiamo quella successiva (assicurandoci che non sia un'altra etichetta)
                    if "CATEGORIA" == testo_upper and i + 1 < len(testi_completi):
                        if testi_completi[i+1].upper() != "POS.":
                            cat = testi_completi[i+1]
                    if "SPECIALITÀ" in testo_upper or "SPECIALITA" in testo_upper:
                        if i + 1 < len(testi_completi) and testi_completi[i+1].upper() != "CATEGORIA":
                            spec = testi_completi[i+1]
                            
                # Uniamo le due parole (es. "SLALOM GIGANTE - GIOVANI / SENIOR")
                if spec and cat:
                    categoria_finale = f"{spec} - {cat}"
                elif cat:
                    categoria_finale = cat
                elif spec:
                    categoria_finale = spec
                else:
                    categoria_finale = "Generale"

                # ⛷️ 2. FASE ATLETI: Torniamo alla classe di prima per pescare in modo chirurgico le classifiche
                elementi_atleti = gara_soup.find_all('span', class_='x-text-content-text-primary')
                testi_atleti = [e.get_text(strip=True) for e in elementi_atleti if len(e.get_text(strip=True)) > 0]
                
                batch_atleti = []
                i = 0
                while i < len(testi_atleti) - 7:
                    if testi_atleti[i].isdigit() and testi_atleti[i+1].isdigit() and len(testi_atleti[i+1]) >= 3:
                        batch_atleti.append({
                            "id_gara_fisi": id_g, 
                            "id_comp_collegata": id_comp, 
                            "posizione": int(testi_atleti[i]),
                            "atleta_nome": testi_atleti[i+2],
                            "societa": testi_atleti[i+4],
                            "categoria": categoria_finale # ECCO LA TUA CATEGORIA PERFETTA!
                        })
                        i += 8
                    else:
                        i += 1
                
                if batch_atleti:
                    supabase.table("Risultati").upsert(batch_atleti).execute()
                    print(f"   ✅ Gara {id_g}: {len(batch_atleti)} atleti salvati in [{categoria_finale}]")
                
                time.sleep(0.5)

        except Exception as e:
            print(f"   ❌ Errore sull'evento {id_comp}: {e}")

if __name__ == "__main__":
    spider_definitivo_con_specialita()
