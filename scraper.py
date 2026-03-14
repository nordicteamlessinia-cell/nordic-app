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
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'})

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

COMITATI_SLUG = {
    'Trentino (TN)': 'trentino', 'Alto Adige (AA)': 'alto-adige', 'Veneto (VE)': 'veneto',
    'Alpi Centrali (AC)': 'alpi-centrali', 'Alpi Occidentali (AOC)': 'alpi-occidentali', 
    'Valdostano (ASIVA)': 'asiva', 'Friuli Venezia Giulia (FVG)': 'friuli-venezia-giulia', 
    'Appennino Emiliano (CAE)': 'appennino-emiliano', 'Appennino Toscano (CAT)': 'appennino-toscano',   
    'Abruzzo (CAB)': 'abruzzo', 'Lazio e Sardegna (CLS)': 'lazio-sardegna', 'Ligure (LIG)': 'ligure',
    'Umbro Marchigiano (CUM)': 'umbro-marchigiano', 'Campano (CAM)': 'campano',
    'Calabro Lucano (CAL)': 'calabro-lucano', 'Pugliese (PUG)': 'pugliese', 'Siculo (SIC)': 'siculo'
}

def calcola_stagione_fisi(data_gara):
    try:
        if not data_gara or data_gara == "N/D": return "2026"
        p = data_gara.split("/")
        if len(p) == 3: return str(int(p[2]) + 1) if int(p[1]) >= 6 else str(p[2])
    except: pass
    return "2026"

def estrai_comitato_reale(item):
    """IL CAPPELLO PARLANTE: Analizza il DNA della gara ed emette la sentenza"""
    if not isinstance(item, dict): return "Sconosciuto"
    
    # 1. Pialliamo tutto in maiuscolo così i programmatori FISI non ci fregano coi nomi strani
    item_u = {str(k).upper(): str(v).strip().upper() for k, v in item.items() if v is not None}
    
    # 2. Controllo livello (Gare Mondiali/Internazionali)
    livello = item_u.get("LIVELLO", "")
    if "WORLD" in livello or "OPA" in livello or "INTERNAZIONAL" in livello:
        return "Nazionale/Internazionale"

    # 3. Controllo Sigla Diretta
    for key in ["COMITATO", "CODICECOMITATO", "SIGLACOMITATO", "CODICECRD"]:
        sigla = item_u.get(key, "")
        if sigla in MAPPA_SIGLE:
            return MAPPA_SIGLE[sigla]

    # 4. IL TEST INFALLIBILE: Codice Società Organizzatrice (Es: TN0014 -> Trentino)
    for key in ["CODICESOCIETA", "SOCIETA", "SOCIETAORGANIZZATRICE"]:
        cod_soc = item_u.get(key, "")
        # Controlliamo prima le sigle a 3 lettere (es. FVG), poi a 2 (es. VE)
        for sigla_mappa in sorted(MAPPA_SIGLE.keys(), key=len, reverse=True):
            if cod_soc.startswith(sigla_mappa):
                return MAPPA_SIGLE[sigla_mappa]
                
    # Se la gara non ha targa, finisce qui per non sporcare i comitati buoni
    return "Nazionale / Sconosciuto"

# =====================================================================
# 🗓️ FASE 1: BOMBARDAMENTO A TAPPETO (Cerca ovunque)
# =====================================================================
def spider_calendari_nazionale():
    print("--- 🚀 FASE 1: RICERCA GLOBALE E SMISTAMENTO ALGORITMICO ---", flush=True)
    
    anno_corrente = datetime.datetime.now().year
    mese_corrente = datetime.datetime.now().month
    anno_massimo = anno_corrente + 1 if mese_corrente >= 6 else anno_corrente
    stagioni_da_scaricare = list(range(2020, anno_massimo + 1))
    
    LISTA_NERA = ["ALPINO", "SLALOM", "GIGANTE", "GS", "SUPER G", "DISCESA", "BIATHLON", "SNOWBOARD", "SKICROSS", "FREESTYLE", "ERBA", "SKELETON", "BOB", "JUMP", "SALTO"]
    
    gare_viste_globali = set()
    all_gare_fondo = []
    
    # Due server da interrogare: Quello Master e quello Multisite
    SERVER_APIS = [
        "https://fisi.org/wp-admin/admin-ajax.php", 
        "https://comitati.fisi.org/wp-admin/admin-ajax.php"
    ]
    
    for anno in stagioni_da_scaricare:
        print(f"\n📅 Scansione Calendario {anno} in corso...", flush=True)
        
        for api_url in SERVER_APIS:
            for sigla, nome_esteso in MAPPA_SIGLE.items():
                offset = 0
                limit = 200
                
                while True:
                    # Forziamo il server a darci questa precisa sigla
                    params = {
                        "action": "competizioni_get_all",
                        "offset": offset,
                        "limit": limit,
                        "idStagione": str(anno),
                        "comitato": sigla 
                    }
                    
                    # Se interroghiamo il server secondario, proviamo anche a ingannarlo con l'URL
                    if "comitati" in api_url:
                        slug = COMITATI_SLUG.get(nome_esteso, "trentino")
                        params["url"] = f"https://comitati.fisi.org/{slug}/calendario/"

                    try:
                        r = session.get(api_url, params=params, timeout=15)
                        data = r.json()
                        
                        if not data or not isinstance(data, list) or len(data) == 0: 
                            break # Pagina vuota

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
                                
                                # 🎩 LA MAGIA DEL CAPPELLO PARLANTE
                                comitato_vero = estrai_comitato_reale(item)

                                record = {
                                    "id_gara_fisi": id_comp, 
                                    "gara_nome": item.get("nome"),
                                    "luogo": item.get("comune", "N/D"), 
                                    "data_gara": item.get("dataInizio", "N/D"), 
                                    "comitato": comitato_vero 
                                }
                                all_gare_fondo.append(record)
                                
                        if len(data) < limit: break
                        offset += limit
                        
                    except Exception:
                        break # In caso di errore server, passa alla sigla successiva
        
        # Salvataggio anno per anno
        if all_gare_fondo:
            supabase.table("Gare").upsert(all_gare_fondo).execute()
            print(f"   ✅ Trovate e smistate {len(all_gare_fondo)} gare finora.", flush=True)

    print("\n🏆 FASE 1 COMPLETATA! I server sono stati setacciati.", flush=True)


# =====================================================================
# ⛷️ FASE 2: ESTRAZIONE ATLETI E TEMPI
# =====================================================================
def spider_atleti_master():
    pass # Disattivata per il test! 

if __name__ == "__main__":
    spider_calendari_nazionale()
    # spider_atleti_master()  # <-- SBLOCCAMI DOPO IL TEST!
