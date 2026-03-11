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

# =====================================================================
# 🗓️ FASE 1: DOWNLOAD CALENDARI (Con Anti-Loop Infinito)
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
        
        slug_sito = percorso_base.split('/')[0]
        url_calendario = f"https://comitati.fisi.org/{percorso_base}/"
        
        # 🕵️‍♂️ L'ALGORITMO HACKER: Cerca l'ID della disciplina
        id_disciplina_fondo = ""
        try:
            res_cal = session.get(url_calendario, timeout=15)
            soup_cal = BeautifulSoup(res_cal.text, 'html.parser')
            for opt in soup_cal.find_all('option'):
                testo = opt.text.upper()
                if "FONDO" in testo or "NORDICO" in testo:
                    val = opt.get('value')
                    if val and val.strip() != "" and val != "-1" and val.upper() != "TUTTE":
                        id_disciplina_fondo = val.strip()
                        break
                        
            if not id_disciplina_fondo:
                for link in soup_cal.find_all('a', href=True):
                    testo = link.text.upper()
                    if "FONDO" in testo or "NORDICO" in testo:
                        import urllib.parse
                        parsed = urllib.parse.urlparse(link['href'])
                        qs = urllib.parse.parse_qs(parsed.query)
                        if 'd' in qs: id_disciplina_fondo = qs['d'][0]; break
                        if 'disciplina' in qs: id_disciplina_fondo = qs['disciplina'][0]; break
        except Exception:
            pass
            
        if id_disciplina_fondo:
            print(f"   🔑 Trovato ID Segreto Fondo: '{id_disciplina_fondo}'")
        else:
            print(f"   ⚠️ ID Fondo non trovato, applico filtro manuale avanzato...")

        all_gare_fondo = []
        
        for anno in stagioni_da_scaricare:
            params = {
                "action": "competizioni_get_all",
                "offset": 0,
                "limit": 100,
                "url": url_calendario, 
                "idStagione": str(anno), 
                "disciplina": id_disciplina_fondo, 
                "dataInizio": "01/01/2010",
                "dataFine": "31/12/2030"
            }
            
            # 🛡️ MEMORIA ANTI-LOOP: Segniamo gli ID già visti in questo anno
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
                        
                        # Se il server ci sta ridando una gara già vista, la ignoriamo
                        if id_comp in gare_viste_questo_anno:
                            continue
                            
                        gare_viste_questo_anno.add(id_comp)
                        nuove_gare_trovate += 1
                        
                        nome_g = item.get("nome", "")
                        luogo_g = item.get("comune", "")
                        data_g = item.get("dataInizio", "")
                        
                        is_fondo = True
                        
                        # Filtro manuale (se non avevamo trovato l'ID segreto)
                        if not id_disciplina_fondo:
                            nome_upper = str(nome_g).upper()
                            if "ALPINO" in nome_upper or "SNOWBOARD" in nome_upper or "SLALOM" in nome_upper or "GIGANTE" in nome_upper or "GS " in nome_upper:
                                is_fondo = False
                            elif "FONDO" not in nome_upper and "NORDICO" not in nome_upper:
                                # Controlla la pagina solo se il nome non è chiaro (riduce i caricamenti lenti)
                                try:
                                    res_test = session.get(f"https://comitati.fisi.org/{slug_sito}/competizione/?idComp={id_comp}", timeout=10)
                                    testo_pagina = res_test.text.upper()
                                    if "FONDO" not in testo_pagina and "NORDICO" not in testo_pagina:
                                        is_fondo = False
                                except:
                                    is_fondo = False

                        if is_fondo:
                            record = {
                                "id_gara_fisi": id_comp, 
                                "gara_nome": nome_g,
                                "luogo": luogo_g, 
                                "data_gara": data_g, 
                                "comitato": nome_comitato 
                            }
                            if record not in all_gare_fondo:
                                all_gare_fondo.append(record)
                    
                    # 🚀 INTERRUTTORE DI SICUREZZA
                    # Se in questa richiesta non abbiamo trovato NESSUNA gara nuova,
                    # significa che il server sta ignorando l'offset. Usciamo dal loop!
                    if nuove_gare_trovate == 0:
                        break
                        
                    params["offset"] += params["limit"]
                    
            except Exception as e:
                print(f"   ❌ Errore di connessione nell'anno {anno}: {e}")
                pass 

        if all_gare_fondo:
            try:
                supabase.table("Gare").upsert(all_gare_fondo).execute()
                print(f"   ✅ SALVATE {len(all_gare_fondo)} GARE DI PURO FONDO (2020 ad oggi).")
            except Exception as db_error:
                print(f"   ❌ Errore durante il salvataggio nel database per {nome_comitato}: {db_error}")
        else:
            print(f"   ⏩ Nessuna gara di Fondo trovata.")
        
        time.sleep(0.5)

# =====================================================================
# ⛷️ FASE 2: SPIDER DEGLI ATLETI
# =====================================================================
def spider_atleti_master_con_tempo():
    print("\n--- 📂 FASE 2: RECUPERO RISULTATI ATLETI DAL DATABASE... ---")
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
            
        slug_sito = COMITATI_FISI.get(nome_comitato).split('/')[0]
        if not slug_sito: 
            continue
        
        stagione_fisi = calcola_stagione_fisi(data_g)
        url_comp = f"https://comitati.fisi.org/{slug_sito}/competizione/?idComp={id_comp}&d={stagione_fisi}"
        
        try:
            res = requests.get(url_comp, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            links = soup.find_all('a', href=True)
            id_sottogare = list(set([l['href'].split('idGara=')[1].split('&')[0] for l in links if 'idGara=' in l['href']]))
            
            if not id_sottogare:
                continue

            print(f"\n🟢 Analizzo: {nome_g} a {luogo_g} ({nome_comitato} | Data: {data_g})")

            for id_g in id_sottogare:
                url_gara = f"https://comitati.fisi.org/{slug_sito}/gara/?idGara={id_g}&idComp={id_comp}&d={stagione_fisi}"
                r_data = requests.get(url_gara, headers=HEADERS, timeout=15)
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
                
                time.sleep(0.3)

        except Exception as e:
            pass

if __name__ == "__main__":
    spider_calendari_fondo_nazionale()
    spider_atleti_master_con_tempo()
