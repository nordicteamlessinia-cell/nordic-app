import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import calendar
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
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})

BASE_URL_AJAX = "https://fisi.org/wp-admin/admin-ajax.php" # <-- PUNTIAMO AL CERVELLO CENTRALE

# 🎯 DECODER DEL DNA (Preciso e senza falsi positivi)
MAPPA_SIGLE = {
    'AA': 'Alto Adige (AA)', 'AC': 'Alpi Centrali (AC)', 'AOC': 'Alpi Occidentali (AOC)',
    'ASIVA': 'Valdostano (ASIVA)', 'CAB': 'Abruzzo (CAB)', 'CAE': 'Appennino Emiliano (CAE)',
    'CAL': 'Calabro Lucano (CAL)', 'CAM': 'Campano (CAM)', 'CAT': 'Appennino Toscano (CAT)',
    'CLS': 'Lazio e Sardegna (CLS)', 'CUM': 'Umbro Marchigiano (CUM)', 'FVG': 'Friuli Venezia Giulia (FVG)',
    'LIG': 'Ligure (LIG)', 'PUG': 'Pugliese (PUG)', 'SIC': 'Siculo (SIC)', 'TN': 'Trentino (TN)',
    'VE': 'Veneto (VE)'
}

def estrai_comitato_reale(item):
    """Analizza i dati grezzi e assegna la gara in modo chirurgico"""
    livello = str(item.get("livello", "")).upper()
    if "WORLD" in livello or "OPA" in livello or "INTERNAZIONAL" in livello:
        return "Internazionale/FIS"

    # 1. Controllo diretto sui campi comitato
    sigla = str(item.get("codiceComitato", "")).strip().upper()
    if not sigla:
        sigla = str(item.get("comitato", "")).strip().upper()
        
    if sigla in MAPPA_SIGLE:
        return MAPPA_SIGLE[sigla]

    # 2. Controllo della targa dello Sci Club (es. FVG0014 -> FVG)
    cod_soc = str(item.get("codiceSocieta", "")).strip().upper()
    if len(cod_soc) >= 2:
        if cod_soc[:3] in MAPPA_SIGLE: return MAPPA_SIGLE[cod_soc[:3]]
        if cod_soc[:2] in MAPPA_SIGLE: return MAPPA_SIGLE[cod_soc[:2]]

    return "Nazionale / Sconosciuto"

# =====================================================================
# 🗓️ FASE 1: ESTRAZIONE MESE PER MESE (A prova di blocco)
# =====================================================================
def spider_calendari_nazionale():
    print("--- 🚀 FASE 1: ESTRAZIONE MENSILE DAL DATABASE CENTRALE ---", flush=True)
    
    anno_corrente = datetime.datetime.now().year
    stagioni_da_scaricare = list(range(2020, anno_corrente + 2))
    LISTA_NERA = ["ALPINO", "SLALOM", "GIGANTE", "GS", "SUPER G", "DISCESA", "BIATHLON", "SNOWBOARD", "SKICROSS", "FREESTYLE", "ERBA", "SKELETON", "BOB", "JUMP", "SALTO"]
    
    gare_viste_globali = set()
    all_gare_fondo = []
    
    for anno in stagioni_da_scaricare:
        print(f"\n📅 Elaborazione Anno {anno}...", flush=True)
        
        # Interroghiamo il server mese per mese!
        for mese in range(1, 13):
            ultimo_giorno = calendar.monthrange(anno, mese)[1]
            data_inizio = f"01/{mese:02d}/{anno}"
            data_fine = f"{ultimo_giorno:02d}/{mese:02d}/{anno}"
            
            params = {
                "action": "competizioni_get_all",
                "dataInizio": data_inizio,
                "dataFine": data_fine,
                "limit": 1000, # Più che sufficienti per un singolo mese
                "offset": 0
            }
            
            try:
                r = session.get(BASE_URL_AJAX, params=params, timeout=20)
                data = r.json()
                
                if not data or not isinstance(data, list):
                    continue

                gare_mese = 0
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
                        
                        comitato_vero = estrai_comitato_reale(item)

                        record = {
                            "id_gara_fisi": id_comp, 
                            "gara_nome": item.get("nome", "Gara Senza Nome"),
                            "luogo": item.get("comune", "N/D"), 
                            "data_gara": item.get("dataInizio", "N/D"), 
                            "comitato": comitato_vero 
                        }
                        all_gare_fondo.append(record)
                        gare_mese += 1
                        
                if gare_mese > 0:
                    print(f"   ❄️ Mese {mese:02d}/{anno}: Trovate {gare_mese} gare di fondo.", flush=True)
                    
            except Exception as e:
                print(f"   ⚠️ Errore di rete nel mese {mese:02d}/{anno}, salto al prossimo.", flush=True)
                
            time.sleep(0.2) # Pausa di cortesia per non far arrabbiare il server

    if all_gare_fondo:
        for i in range(0, len(all_gare_fondo), 1000):
            pacchetto = all_gare_fondo[i:i+1000]
            supabase.table("Gare").upsert(pacchetto).execute()
        print(f"\n✅ TRIONFO: {len(all_gare_fondo)} gare di Fondo recuperate in totale!", flush=True)
    else:
        print("\n❌ Nessuna gara trovata.", flush=True)

# =====================================================================
# ⛷️ FASE 2: ESTRAZIONE ATLETI E TEMPI
# =====================================================================
def spider_atleti_master():
    pass # In pausa per il test dei calendari

if __name__ == "__main__":
    spider_calendari_nazionale()
    # spider_atleti_master()
