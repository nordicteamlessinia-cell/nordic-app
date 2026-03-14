import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import datetime
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
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'})

# Torniamo al server che ci rispondeva, ma lo usiamo in modo più intelligente
BASE_URL_AJAX = "https://comitati.fisi.org/wp-admin/admin-ajax.php"

# 🎯 LE CHIAVI DI ACCESSO PER IL DATABASE
MAPPA_SIGLE = {
    'AA': 'Alto Adige (AA)', 'AC': 'Alpi Centrali (AC)', 'AOC': 'Alpi Occidentali (AOC)',
    'ASIVA': 'Valdostano (ASIVA)', 'CAB': 'Abruzzo (CAB)', 'CAE': 'Appennino Emiliano (CAE)',
    'CAL': 'Calabro Lucano (CAL)', 'CAM': 'Campano (CAM)', 'CAT': 'Appennino Toscano (CAT)',
    'CLS': 'Lazio e Sardegna (CLS)', 'CUM': 'Umbro Marchigiano (CUM)', 'FVG': 'Friuli Venezia Giulia (FVG)',
    'LIG': 'Ligure (LIG)', 'PUG': 'Pugliese (PUG)', 'SIC': 'Siculo (SIC)', 'TN': 'Trentino (TN)',
    'VE': 'Veneto (VE)'
}

def estrai_comitato_reale(item, sigla_richiesta):
    """Il Test del DNA finale"""
    livello = str(item.get("livello", "")).upper()
    if "WORLD" in livello or "OPA" in livello or "INTERNAZIONAL" in livello:
        return "Nazionale/Internazionale"

    # 1. Leggiamo la sigla dal JSON
    c = str(item.get("codiceComitato", "")).strip().upper()
    if not c: c = str(item.get("comitato", "")).strip().upper()
    if c in MAPPA_SIGLE: return MAPPA_SIGLE[c]

    # 2. Leggiamo la targa dello Sci Club (es. FVG0014)
    soc = str(item.get("codiceSocieta", "")).strip().upper()
    for s in sorted(MAPPA_SIGLE.keys(), key=len, reverse=True):
        if soc.startswith(s): return MAPPA_SIGLE[s]

    # 3. Se tutto fallisce, gli assegniamo la sigla che avevamo richiesto all'API
    if sigla_richiesta in MAPPA_SIGLE: return MAPPA_SIGLE[sigla_richiesta]
    
    return "Sconosciuto"

# =====================================================================
# 🗓️ FASE 1: INTERROGAZIONE CHIRURGICA DEL DATABASE
# =====================================================================
def spider_calendari_nazionale():
    print("--- 🚀 FASE 1: SCANSIONE CHIRURGICA PER COMITATO ---", flush=True)
    
    anno_corrente = datetime.datetime.now().year
    mese_corrente = datetime.datetime.now().month
    anno_massimo = anno_corrente + 1 if mese_corrente >= 6 else anno_corrente
    stagioni_da_scaricare = list(range(2020, anno_massimo + 1))
    
    LISTA_NERA = ["ALPINO", "SLALOM", "GIGANTE", "GS", "SUPER G", "DISCESA", "BIATHLON", "SNOWBOARD", "SKICROSS", "FREESTYLE", "ERBA", "SKELETON", "BOB", "JUMP", "SALTO"]
    gare_viste_globali = set()
    totale_salvate = 0
    
    for anno in stagioni_da_scaricare:
        print(f"\n📅 Elaborazione Anno {anno}...", flush=True)
        all_gare_fondo = []
        
        # Facciamo una richiesta specifica per ogni singola regione!
        for sigla, nome_esteso in MAPPA_SIGLE.items():
            offset = 0
            limit = 200
            
            while True:
                # Questa è la chiave: forziamo il comitato nei parametri dell'API
                params = {
                    "action": "competizioni_get_all",
                    "idStagione": str(anno),
                    "comitato": sigla, 
                    "limit": limit,
                    "offset": offset
                }
                
                try:
                    r = session.get(BASE_URL_AJAX, params=params, timeout=15)
                    data = r.json()
                    
                    if not data or not isinstance(data, list) or len(data) == 0:
                        break # Pagina vuota, passiamo alla prossima sigla
                        
                    for item in data:
                        id_comp = str(item.get("idCompetizione"))
                        if id_comp in gare_viste_globali: continue
                            
                        disciplina = str(item.get("disciplina", "")).upper()
                        nome_gara = str(item.get("nome", "")).upper()
                        
                        is_fondo = any(k in disciplina for k in ["FONDO", "LANGLAUF", "NORDICO", "XC"]) or \
                                   any(k in nome_gara for k in ["FONDO", "LANGLAUF", "NORDICO", "CROSS COUNTRY", "XC"])
                        is_proibita = any(k in nome_gara for k in LISTA_NERA) or any(k in disciplina for k in LISTA_NERA)
                        
                        if is_fondo and not is_proibita:
                            gare_viste_globali.add(id_comp)
                            
                            comitato_vero = estrai_comitato_reale(item, sigla)

                            record = {
                                "id_gara_fisi": id_comp, 
                                "gara_nome": item.get("nome", "Gara Senza Nome"),
                                "luogo": item.get("comune", "N/D"), 
                                "data_gara": item.get("dataInizio", "N/D"), 
                                "comitato": comitato_vero 
                            }
                            all_gare_fondo.append(record)
                            
                    if len(data) < limit: break
                    offset += limit
                    
                except Exception:
                    break # In caso di errore, skippa
            
            time.sleep(0.1)
            
        if all_gare_fondo:
            supabase.table("Gare").upsert(all_gare_fondo).execute()
            totale_salvate += len(all_gare_fondo)
            print(f"   ✅ Anno {anno} concluso: Salvate {len(all_gare_fondo)} gare di fondo.", flush=True)
        else:
            print(f"   ⏩ Anno {anno} concluso: Nessuna gara di fondo trovata.", flush=True)

    print(f"\n🏆 FASE 1 COMPLETATA! Totale Assoluto Gare Italia: {totale_salvate}", flush=True)

if __name__ == "__main__":
    spider_calendari_nazionale()
    # spider_atleti_master() <-- Fase 2 disattivata per il check veloce
