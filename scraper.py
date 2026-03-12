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

# 🗺️ IL DIZIONARIO ESATTO E DEFINITIVO
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

# =====================================================================
# 🗓️ FASE 1: DOWNLOAD CALENDARI AJAX (CON ID DISCIPLINA UNIVERSALE)
# =====================================================================
def spider_calendari_fondo_nazionale():
    print("\n--- 📅 FASE 1: DOWNLOAD CALENDARI STORICI (SOLO FONDO) ---")
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    anno_corrente = datetime.datetime.now().year
    mese_corrente = datetime.datetime.now().month
    anno_massimo = anno_corrente + 1 if mese_corrente >= 6 else anno_corrente
    stagioni_da_scaricare = list(range(2020, anno_massimo + 1))
    
    for nome_comitato, percorso_base in COMITATI_FISI.items():
        print(f"\n🌍 Analizzo: {nome_comitato}...")
        
        url_calendario = f"https://comitati.fisi.org/{percorso_base}/"
        all_gare_fondo = []
        
        for anno in stagioni_da_scaricare:
            # 🎯 IL SEGRETO SVELATO:
            # "190" è il codice universale per lo Sci di Fondo nel DB della FISI!
            params = {
                "action": "competizioni_get_all",
                "offset": 0,
                "limit": 100,
                "url": url_calendario, 
                "idStagione": str(anno), 
                "disciplina": "190", # 👈 MAGIA PURA: Chiede SOLO il Fondo!
                "dataInizio": "01/01/2010",
                "dataFine": "31/12/2030"
            }
            
            gare_viste_questo_anno = set()
            
            try:
                while True:
                    r = session.get(BASE_URL_AJAX, params=params, timeout=15)
                    if r.status_code != 200: break
                    data = r.json()
                    if not data: break

                    nuove_gare_trovate = 0

                    for item in data:
                        id_comp = str(item.get("idCompetizione"))
                        if id_comp in gare_viste_questo_anno:
                            continue
                            
                        gare_viste_questo_anno.add(id_comp)
                        nuove_gare_trovate += 1
                        
                        nome_g = str(item.get("nome", ""))
                        luogo_g = str(item.get("comune", ""))
                        data_g = str(item.get("dataInizio", ""))
                        
                        record = {
                            "id_gara_fisi": id_comp, 
                            "gara_nome": nome_g,
                            "luogo": luogo_g, 
                            "data_gara": data_g, 
                            "comitato": nome_comitato 
                        }
                        if record not in all_gare_fondo:
                            all_gare_fondo.append(record)
                    
                    if nuove_gare_trovate == 0:
                        break
                        
                    params["offset"] += params["limit"]
                    
            except Exception:
                pass 

        if all_gare_fondo:
            try:
                supabase.table("Gare").upsert(all_gare_fondo).execute()
                print(f"   ✅ SALVATE {len(all_gare_fondo)} GARE DI PURO FONDO (2020-Oggi).")
            except Exception as e:
                print(f"   ❌ Errore Database: {e}")
        else:
            print(f"   ⏩ Nessuna gara di Fondo trovata.")
        
        time.sleep(0.5)

# =====================================================================
# ⛷️ FASE 2: ESTRAZIONE ATLETI DALL'HTML (BLINDATA CONTRO I CRASH)
# =====================================================================
def spider_atleti_master_con_tempo():
    print("\n--- 📂 FASE 2: RECUPERO RISULTATI ATLETI DAL DATABASE... ---")
    session = requests.Session()
    session.headers.update(HEADERS)
    
    try:
        gare_db = supabase.table("Gare").select("id_gara_fisi, data_gara, gara_nome, luogo, comitato").execute()
        lista_gare = gare_db.data
    except Exception as e:
        print(f"❌ Errore fatale nella lettura dal Database: {e}")
        return

    print(f"--- ⏱️ INIZIO ESTRAZIONE ATLETI --- (Trovate {len(lista_gare)} gare nel DB)")

    for gara in lista_gare:
        id_comp = gara.get('id_gara_fisi')
        data_g = gara.get('data_gara')
        nome_g = gara.get('gara_nome')
        luogo_g = gara.get('luogo')
        nome_comitato = gara.get('comitato')
        
        if not id_comp or not nome_comitato or nome_comitato == 'Generico': 
            continue
            
        percorso = COMITATI_FISI.get(nome_comitato)
        if not percorso:
            continue
        slug_sito = percorso.split('/')[0]
        
        stagione_fisi = calcola_stagione_fisi(data_g)
        url_comp = f"https://comitati.fisi.org/{slug_sito}/competizione/?idComp={id_comp}&d={stagione_fisi}"
        
        try:
            res = session.get(url_comp, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            testo_pagina = soup.get_text().upper()
            
            # CANCELLO DI SICUREZZA: Se c'è scritto Alpino/Snowboard ed è un falso positivo, la cestiniamo
            if "ALPINO" in testo_pagina or "SNOWBOARD" in testo_pagina or "BIATHLON" in testo_pagina:
                if "FONDO" not in testo_pagina and "NORDICO" not in testo_pagina and "LANGLAUF" not in testo_pagina:
                    print(f"   🗑️ ELIMINATA: {nome_g} (Falso positivo rimossa dal DB)")
                    supabase.table("Gare").delete().eq("id_gara_fisi", id_comp).execute()
                    continue
            
            links = soup.find_all('a', href=True)
            id_sottogare = list(set([l['href'].split('idGara=')[1].split('&')[0] for l in links if 'idGara=' in l['href']]))
            
            if not id_sottogare:
                continue

            print(f"\n🟢 Analizzo: {nome_g} a {luogo_g}")

            for id_g in id_sottogare:
                url_gara = f"https://comitati.fisi.org/{slug_sito}/gara/?idGara={id_g}&idComp={id_comp}&d={stagione_fisi}"
                r_data = session.get(url_gara, timeout=15)
                gara_soup = BeautifulSoup(r_data.text, 'html.parser')
                
                testi_completi = list(gara_soup.stripped_strings)
                cat, spec = "", ""
                for i, t in enumerate(testi_completi):
                    testo_upper = t.upper()
                    if "CATEGORIA" == testo_upper and i + 1 < len(testi_completi) and testi_completi[i+1].upper() != "POS.":
                        cat = testi_completi[i+1]
                    if "SPECIALITÀ" in testo_upper or "SPECIALITA" in testo_upper:
                        if i + 1 < len(testi_completi) and testi_completi[i+1].upper() != "CATEGORIA":
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
                    print(f"   ✅ Salvati {len(batch_atleti)} atleti per la gara!")

        except Exception:
            pass

if __name__ == "__main__":
    spider_calendari_fondo_nazionale()
    spider_atleti_master_con_tempo()
