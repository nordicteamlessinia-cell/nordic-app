import os
import requests
import time
import datetime
from bs4 import BeautifulSoup
from supabase import create_client

# 🟢 INIZIALIZZAZIONE SUPABASE
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'}
BASE_URL_AJAX = "https://comitati.fisi.org/wp-admin/admin-ajax.php"

# 🗺️ IL DIZIONARIO PERFETTO
COMITATI_FISI = {
    'Abruzzo (CAB)': 'abruzzo/calendario',
    'Alto Adige (AA)': 'altoadige/calendario-gare',
    'Alpi Centrali (AC)': 'alpicentrali/calendario-gare',
    'Alpi Occidentali (AOC)': 'aoc/calendario',
    'Appennino Emiliano (CAE)': 'cae/calendario',
    'Appennino Toscano (CAT)': 'cat/calendario',
    'Calabro Lucano (CAL)': 'cal/calendario',
    'Campano (CAM)': 'campano/calendario',
    'Friuli Venezia Giulia (FVG)': 'fvg/calendario',
    'Lazio e Sardegna (CLS)': 'cls/calendario',
    'Ligure (LIG)': 'ligure/calendario',
    'Pugliese (PUG)': 'pugliese/calendario',
    'Siculo (SIC)': 'siculo/calendario',
    'Trentino (TN)': 'trentino/calendario-gare',
    'Umbro Marchigiano (CUM)': 'cum/calendario',
    'Valdostano (ASIVA)': 'asiva/calendario',
    'Veneto (VE)': 'veneto/calendario'
}

def calcola_stagione_fisi(data_gara):
    try:
        if not data_gara or data_gara == "N/D": return "2026"
        p = data_gara.split("/")
        if len(p) == 3:
            return str(int(p[2]) + 1) if int(p[1]) >= 6 else str(p[2])
    except: pass
    return "2026"

def esegui_spider_completo_e_blindato():
    print("\n--- 🚀 INIZIO ESTRAZIONE TOTALE (MEMORIA ANTI-ALPINO) ---")
    session = requests.Session()
    session.headers.update(HEADERS)
    
    anno_corrente = datetime.datetime.now().year
    mese_corrente = datetime.datetime.now().month
    anno_massimo = anno_corrente + 1 if mese_corrente >= 6 else anno_corrente
    stagioni_da_scaricare = list(range(2020, anno_massimo + 1))
    
    for nome_comitato, percorso_base in COMITATI_FISI.items():
        print(f"\n=======================================================")
        print(f"🌍 Analizzo Comitato: {nome_comitato}")
        print(f"=======================================================")
        
        slug_sito = percorso_base.split('/')[0]
        url_calendario = f"https://comitati.fisi.org/{percorso_base}/"
        
        for anno in stagioni_da_scaricare:
            print(f"\n   ⏳ Cerco gare per l'anno {anno}...")
            params = {
                "action": "competizioni_get_all",
                "offset": 0,
                "limit": 100,
                "url": url_calendario, 
                "idStagione": str(anno), 
                "disciplina": "", 
                "dataInizio": "01/01/2010",
                "dataFine": "31/12/2030"
            }
            
            gare_viste_questo_anno = set()
            
            while True:
                try:
                    r = session.get(BASE_URL_AJAX, params=params, timeout=15)
                    if r.status_code != 200: break
                    data = r.json()
                    if not data: break
                    
                    nuove_gare = 0
                    for item in data:
                        id_comp = str(item.get("idCompetizione"))
                        if id_comp in gare_viste_questo_anno: continue
                        
                        gare_viste_questo_anno.add(id_comp)
                        nuove_gare += 1
                        
                        nome_g = str(item.get("nome", ""))
                        luogo_g = str(item.get("comune", ""))
                        data_g = str(item.get("dataInizio", ""))
                        
                        # --- 🛑 FILTRO IN MEMORIA (NON SALVIAMO ANCORA NULLA!) ---
                        nome_upper = nome_g.upper()
                        
                        # 1. Scarto immediato basato sul nome (Veloce)
                        if any(x in nome_upper for x in ["ALPINO", "SNOWBOARD", "SLALOM", "GIGANTE", "GS", "SUPER G", "DISCESA", "BIATHLON", "SKICROSS", "ALPENCUP"]):
                            continue # È chiaramente un'altra disciplina, ignoriamo all'istante!
                            
                        is_fondo = False
                        
                        # 2. Conferma immediata basata sul nome (Veloce)
                        if any(x in nome_upper for x in ["FONDO", "NORDICO", "LANGLAUF", "CROSS COUNTRY", "XC"]):
                            is_fondo = True
                        
                        # 3. Controllo approfondito sull'HTML se il nome è ambiguo
                        if not is_fondo:
                            url_test = f"https://comitati.fisi.org/{slug_sito}/competizione/?idComp={id_comp}"
                            try:
                                res_test = session.get(url_test, timeout=10)
                                testo_pagina = res_test.text.upper()
                                if "FONDO" in testo_pagina or "NORDICO" in testo_pagina or "LANGLAUF" in testo_pagina or "CROSS COUNTRY" in testo_pagina:
                                    # Assicuriamoci che non sia un falso positivo
                                    if "ALPINO" not in testo_pagina and "SNOWBOARD" not in testo_pagina:
                                        is_fondo = True
                            except:
                                pass
                        
                        # Se NON è fondo, la ignoriamo definitivamente.
                        if not is_fondo:
                            continue
                            
                        # --- ✅ E' FONDO AL 100%! ORA SALVIAMO ED ESTRAIAMO GLI ATLETI ---
                        print(f"   🎿 Trovata Gara di Fondo: {nome_g} ({data_g})")
                        
                        # 1. Salviamo la Gara in DB
                        record_gara = {
                            "id_gara_fisi": id_comp, 
                            "gara_nome": nome_g,
                            "luogo": luogo_g, 
                            "data_gara": data_g, 
                            "comitato": nome_comitato 
                        }
                        supabase.table("Gare").upsert([record_gara]).execute()
                        
                        # 2. Apriamo la classifica ed estraiamo subito gli Atleti!
                        stagione_fisi = calcola_stagione_fisi(data_g)
                        url_comp = f"https://comitati.fisi.org/{slug_sito}/competizione/?idComp={id_comp}&d={stagione_fisi}"
                        try:
                            res_class = session.get(url_comp, timeout=15)
                            soup_class = BeautifulSoup(res_class.text, 'html.parser')
                            links = soup_class.find_all('a', href=True)
                            id_sottogare = list(set([l['href'].split('idGara=')[1].split('&')[0] for l in links if 'idGara=' in l['href']]))
                            
                            for id_g in id_sottogare:
                                url_gara = f"https://comitati.fisi.org/{slug_sito}/gara/?idGara={id_g}&idComp={id_comp}&d={stagione_fisi}"
                                r_data = session.get(url_gara, timeout=15)
                                gara_soup = BeautifulSoup(r_data.text, 'html.parser')
                                
                                testi_completi = list(gara_soup.stripped_strings)
                                cat, spec = "", ""
                                for i, t in enumerate(testi_completi):
                                    if "CATEGORIA" == t.upper() and i + 1 < len(testi_completi):
                                        cat = testi_completi[i+1]
                                    if "SPECIALITÀ" in t.upper() or "SPECIALITA" in t.upper():
                                        if i + 1 < len(testi_completi):
                                            spec = testi_completi[i+1]
                                            
                                categoria_finale = f"{spec} - {cat}".strip(" -") if spec or cat else "Generale"

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
                                            "tempo": testi_atleti[i+5], 
                                            "categoria": categoria_finale,
                                            "gara_nome": nome_g,
                                            "luogo": luogo_g,
                                            "data_gara": data_g,
                                            "comitato": nome_comitato 
                                        })
                                        i += 8
                                    else:
                                        i += 1
                                        
                                if batch_atleti:
                                    supabase.table("Risultati").upsert(batch_atleti).execute()
                                    print(f"      ✅ Salvati {len(batch_atleti)} atleti.")
                        except Exception as e:
                            pass 
                            
                    # Anti-Loop
                    if nuove_gare == 0: break
                    params["offset"] += params["limit"]
                    
                except Exception:
                    break 

if __name__ == "__main__":
    esegui_spider_completo_e_blindato()
