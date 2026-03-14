import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import datetime
from bs4 import BeautifulSoup
from supabase import create_client

# 🟢 INIZIALIZZAZIONE SUPABASE
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 🛡️ ARMATURA DI RETE
session = requests.Session()
retries = Retry(total=5, backoff_factor=2, status_forcelist=[ 429, 500, 502, 503, 504 ])
session.mount('https://', HTTPAdapter(max_retries=retries))
session.mount('http://', HTTPAdapter(max_retries=retries))

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'}
session.headers.update(HEADERS)

BASE_URL_AJAX = "https://comitati.fisi.org/wp-admin/admin-ajax.php"

# 🗺️ ELENCO COMITATI PER LE CHIAMATE API
COMITATI_FISI = {
    'Trentino (TN)': 'trentino', 'Alto Adige (AA)': 'alto-adige', 'Veneto (VE)': 'veneto',
    'Alpi Centrali (AC)': 'alpi-centrali', 'Alpi Occidentali (AOC)': 'alpi-occidentali', 
    'Valdostano (ASIVA)': 'asiva', 'Friuli Venezia Giulia (FVG)': 'friuli-venezia-giulia', 
    'Appennino Emiliano (CAE)': 'appennino-emiliano', 'Appennino Toscano (CAT)': 'appennino-toscano',   
    'Abruzzo (CAB)': 'abruzzo', 'Lazio e Sardegna (CLS)': 'lazio-sardegna', 'Ligure (LIG)': 'ligure',
    'Umbro Marchigiano (CUM)': 'umbro-marchigiano', 'Campano (CAM)': 'campano',
    'Calabro Lucano (CAL)': 'calabro-lucano', 'Pugliese (PUG)': 'pugliese', 'Siculo (SIC)': 'siculo'
}

# 🎯 DECODER DEL DNA (Infallibile)
MAPPA_SIGLE = {
    'CAB': 'Abruzzo (CAB)', 'AA': 'Alto Adige (AA)', 'AC': 'Alpi Centrali (AC)',
    'AOC': 'Alpi Occidentali (AOC)', 'CAE': 'Appennino Emiliano (CAE)',
    'CAT': 'Appennino Toscano (CAT)', 'CAL': 'Calabro Lucano (CAL)',
    'CAM': 'Campano (CAM)', 'FVG': 'Friuli Venezia Giulia (FVG)',
    'CLS': 'Lazio e Sardegna (CLS)', 'LIG': 'Ligure (LIG)',
    'PUG': 'Pugliese (PUG)', 'SIC': 'Siculo (SIC)', 'TN': 'Trentino (TN)',
    'CUM': 'Umbro Marchigiano (CUM)', 'ASIVA': 'Valdostano (ASIVA)',
    'VA': 'Valdostano (ASIVA)', 'VE': 'Veneto (VE)'
}

def calcola_stagione_fisi(data_gara):
    try:
        if not data_gara or data_gara == "N/D": return "2026"
        p = data_gara.split("/")
        if len(p) == 3: return str(int(p[2]) + 1) if int(p[1]) >= 6 else str(p[2])
    except: pass
    return "2026"

def estrai_comitato_reale(item, fallback_comitato):
    """Il Test del DNA: cerca le sigle nascoste nel JSON della gara"""
    # 1. Cerca il comitato dichiarato nell'API
    sigla = str(item.get("codiceComitato", "")).strip().upper()
    if not sigla:
        sigla = str(item.get("comitato", "")).strip().upper()

    if sigla in MAPPA_SIGLE:
        return MAPPA_SIGLE[sigla]

    # 2. Cerca nel Codice Società Organizzatrice (Es. VE0036)
    cod_soc = str(item.get("codiceSocieta", "")).strip().upper()
    for sigla_mappa in sorted(MAPPA_SIGLE.keys(), key=len, reverse=True):
        if cod_soc.startswith(sigla_mappa):
            return MAPPA_SIGLE[sigla_mappa]

    # 3. Fallback per le vere gare internazionali
    livello = str(item.get("livello", "")).upper()
    if "WORLD" in livello or "OPA" in livello or "INTERNAZIONAL" in livello:
        return "Internazionale/FIS"

    # 4. Nessuna traccia di DNA? Ci fidiamo del portale che stiamo interrogando.
    return fallback_comitato

# =====================================================================
# 🗓️ FASE 1: DOWNLOAD CALENDARI (Paginazione + DNA)
# =====================================================================
def spider_calendari_nazionale():
    print("--- 🚀 FASE 1: SINCRONIZZAZIONE CALENDARI NAZIONALI ---", flush=True)
    
    anno_corrente = datetime.datetime.now().year
    mese_corrente = datetime.datetime.now().month
    anno_massimo = anno_corrente + 1 if mese_corrente >= 6 else anno_corrente
    stagioni_da_scaricare = list(range(2020, anno_massimo + 1))
    
    LISTA_NERA = ["ALPINO", "SLALOM", "GIGANTE", "GS", "SUPER G", "DISCESA", "BIATHLON", "SNOWBOARD", "SKICROSS", "FREESTYLE", "ERBA", "SKELETON", "BOB", "JUMP", "SALTO"]
    
    gare_viste_globali = set()
    totale_gare_salvate = 0
    
    for nome_comitato, slug_sito in COMITATI_FISI.items():
        print(f"\n🌍 Bussiamo alla porta di: {nome_comitato}...", flush=True)
        all_gare_fondo = []
        
        # Troviamo la porta giusta
        url_chiave = f"https://comitati.fisi.org/{slug_sito}/calendario/"
        for percorso in ["calendario", "calendario-gare", "gare", "competizioni", ""]:
            test_url = f"https://comitati.fisi.org/{slug_sito}/{percorso}/" if percorso else f"https://comitati.fisi.org/{slug_sito}/"
            try:
                test_params = {"action": "competizioni_get_all", "offset": 0, "limit": 2, "url": test_url, "idStagione": str(anno_massimo)}
                r_test = session.get(BASE_URL_AJAX, params=test_params, timeout=10)
                if r_test.status_code == 200 and isinstance(r_test.json(), list):
                    url_chiave = test_url
                    print(f"   🔑 Server agganciato: {url_chiave}", flush=True)
                    break
            except Exception:
                pass

        for anno in stagioni_da_scaricare:
            offset = 0
            limit = 100 # Chiediamo 100 gare alla volta, senza stancare il server
            
            while True:
                params = {
                    "action": "competizioni_get_all",
                    "offset": offset,
                    "limit": limit, 
                    "url": url_chiave, 
                    "idStagione": str(anno)
                }
                
                try:
                    r = session.get(BASE_URL_AJAX, params=params, timeout=30)
                    data = r.json()
                    if not data or not isinstance(data, list) or len(data) == 0: 
                        break # Pagina vuota, anno finito

                    for item in data:
                        id_comp = str(item.get("idCompetizione"))
                        
                        if id_comp in gare_viste_globali:
                            continue # Già salvata
                            
                        disciplina = str(item.get("disciplina", "")).upper()
                        nome_gara = str(item.get("nome", "")).upper()
                        
                        is_fondo = any(k in disciplina for k in ["FONDO", "LANGLAUF", "NORDICO", "XC"]) or \
                                   any(k in nome_gara for k in ["FONDO", "LANGLAUF", "NORDICO", "CROSS COUNTRY", "XC"])
                        is_proibita = any(k in nome_gara for k in LISTA_NERA) or any(k in disciplina for k in LISTA_NERA)
                        
                        if is_fondo and not is_proibita:
                            gare_viste_globali.add(id_comp)
                            
                            # 🎯 TEST DEL DNA
                            comitato_vero = estrai_comitato_reale(item, nome_comitato)

                            record = {
                                "id_gara_fisi": id_comp, 
                                "gara_nome": item.get("nome"),
                                "luogo": item.get("comune", "N/D"), 
                                "data_gara": item.get("dataInizio", "N/D"), 
                                "comitato": comitato_vero 
                            }
                            all_gare_fondo.append(record)
                    
                    if len(data) < limit:
                        break # Ultima pagina raggiunta
                        
                    offset += limit 
                    
                except Exception:
                    break

        if all_gare_fondo:
            supabase.table("Gare").upsert(all_gare_fondo).execute()
            totale_gare_salvate += len(all_gare_fondo)
            print(f"   ✅ Salvate {len(all_gare_fondo)} gare estratte da questo server.", flush=True)
        else:
            print(f"   ⏩ Nessuna gara compatibile trovata.", flush=True)
        
        time.sleep(0.3)
        
    print(f"\n🏆 FASE 1 COMPLETATA! Totale Gare Fondo in Italia: {totale_gare_salvate}", flush=True)

# =====================================================================
# ⛷️ FASE 2: ESTRAZIONE ATLETI E TEMPI (Da lanciare DOPO il test)
# =====================================================================
def spider_atleti_master():
    pass # Lasciamo vuoto per il test

if __name__ == "__main__":
    spider_calendari_nazionale()
    # spider_atleti_master()  # <-- SBLOCCAMI DOPO IL TEST!
