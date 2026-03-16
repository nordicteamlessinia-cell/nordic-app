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

BASE_URL_AJAX = "https://comitati.fisi.org/wp-admin/admin-ajax.php"

# Interroghiamo solo i server principali per pescare tutte le gare grezze d'Italia
COMITATI_SPAZZOLINI = ['trentino', 'veneto', 'asiva', 'alpi-centrali', 'siculo'] 

# 🎯 DECODER UFFICIALE DEI COMITATI
MAPPA_COMITATI = {
    'AA': 'Alto Adige (AA)', 'AC': 'Alpi Centrali (AC)', 'AOC': 'Alpi Occidentali (AOC)',
    'ASIVA': 'Valdostano (ASIVA)', 'CAB': 'Abruzzo (CAB)', 'CAE': 'Appennino Emiliano (CAE)', 
    'CAL': 'Calabro Lucano (CAL)', 'CAM': 'Campano (CAM)', 'CAT': 'Appennino Toscano (CAT)', 
    'CLS': 'Lazio e Sardegna (CLS)', 'CUM': 'Umbro Marchigiano (CUM)', 'FVG': 'Friuli Venezia Giulia (FVG)', 
    'LIG': 'Ligure (LIG)', 'PUG': 'Pugliese (PUG)', 'SIC': 'Siculo (SIC)', 'TN': 'Trentino (TN)', 
    'VE': 'Veneto (VE)', 'GM': 'Gruppi Militari (GM)'
}

# 🗺️ LA CHIAVE DI VOLTA: MAPPA DELLE 107 PROVINCE ITALIANE
MAPPA_PROVINCE = {
    # TRENTINO ALTO ADIGE
    'TN': 'Trentino (TN)', 'BZ': 'Alto Adige (AA)', 
    # VALLE D'AOSTA
    'AO': 'Valdostano (ASIVA)',
    # PIEMONTE (AOC)
    'AL': 'Alpi Occidentali (AOC)', 'AT': 'Alpi Occidentali (AOC)', 'BI': 'Alpi Occidentali (AOC)',
    'CN': 'Alpi Occidentali (AOC)', 'NO': 'Alpi Occidentali (AOC)', 'TO': 'Alpi Occidentali (AOC)',
    'VB': 'Alpi Occidentali (AOC)', 'VC': 'Alpi Occidentali (AOC)',
    # LOMBARDIA (AC)
    'BG': 'Alpi Centrali (AC)', 'BS': 'Alpi Centrali (AC)', 'CO': 'Alpi Centrali (AC)',
    'CR': 'Alpi Centrali (AC)', 'LC': 'Alpi Centrali (AC)', 'LO': 'Alpi Centrali (AC)',
    'MN': 'Alpi Centrali (AC)', 'MI': 'Alpi Centrali (AC)', 'MB': 'Alpi Centrali (AC)',
    'PV': 'Alpi Centrali (AC)', 'SO': 'Alpi Centrali (AC)', 'VA': 'Alpi Centrali (AC)', # Varese!
    # VENETO (VE)
    'BL': 'Veneto (VE)', 'PD': 'Veneto (VE)', 'RO': 'Veneto (VE)', 'TV': 'Veneto (VE)',
    'VE': 'Veneto (VE)', 'VR': 'Veneto (VE)', 'VI': 'Veneto (VE)',
    # FRIULI (FVG)
    'GO': 'Friuli Venezia Giulia (FVG)', 'PN': 'Friuli Venezia Giulia (FVG)',
    'TS': 'Friuli Venezia Giulia (FVG)', 'UD': 'Friuli Venezia Giulia (FVG)',
    # LIGURIA (LIG)
    'GE': 'Ligure (LIG)', 'IM': 'Ligure (LIG)', 'SP': 'Ligure (LIG)', 'SV': 'Ligure (LIG)',
    # EMILIA ROMAGNA (CAE)
    'BO': 'Appennino Emiliano (CAE)', 'FE': 'Appennino Emiliano (CAE)', 'FC': 'Appennino Emiliano (CAE)',
    'MO': 'Appennino Emiliano (CAE)', 'PR': 'Appennino Emiliano (CAE)', 'PC': 'Appennino Emiliano (CAE)',
    'RA': 'Appennino Emiliano (CAE)', 'RE': 'Appennino Emiliano (CAE)', 'RN': 'Appennino Emiliano (CAE)',
    # TOSCANA (CAT)
    'AR': 'Appennino Toscano (CAT)', 'FI': 'Appennino Toscano (CAT)', 'GR': 'Appennino Toscano (CAT)',
    'LI': 'Appennino Toscano (CAT)', # Livorno!
    'LU': 'Appennino Toscano (CAT)', 'MS': 'Appennino Toscano (CAT)', 'PI': 'Appennino Toscano (CAT)',
    'PT': 'Appennino Toscano (CAT)', 'PO': 'Appennino Toscano (CAT)', 'SI': 'Appennino Toscano (CAT)',
    # UMBRIA E MARCHE (CUM)
    'PG': 'Umbro Marchigiano (CUM)', 'TR': 'Umbro Marchigiano (CUM)', 'AN': 'Umbro Marchigiano (CUM)',
    'AP': 'Umbro Marchigiano (CUM)', 'FM': 'Umbro Marchigiano (CUM)', 'MC': 'Umbro Marchigiano (CUM)',
    'PU': 'Umbro Marchigiano (CUM)',
    # LAZIO E SARDEGNA (CLS)
    'FR': 'Lazio e Sardegna (CLS)', 'LT': 'Lazio e Sardegna (CLS)', 'RI': 'Lazio e Sardegna (CLS)',
    'RM': 'Lazio e Sardegna (CLS)', 'VT': 'Lazio e Sardegna (CLS)', 'CA': 'Lazio e Sardegna (CLS)',
    'NU': 'Lazio e Sardegna (CLS)', 'OR': 'Lazio e Sardegna (CLS)', 'SS': 'Lazio e Sardegna (CLS)',
    'SU': 'Lazio e Sardegna (CLS)',
    # ABRUZZO (CAB)
    'CH': 'Abruzzo (CAB)', 'AQ': 'Abruzzo (CAB)', 'PE': 'Abruzzo (CAB)', 'TE': 'Abruzzo (CAB)',
    # CAMPANIA E MOLISE (CAM)
    'AV': 'Campano (CAM)', 'BN': 'Campano (CAM)', 'CE': 'Campano (CAM)', 'NA': 'Campano (CAM)',
    'SA': 'Campano (CAM)', 'CB': 'Campano (CAM)', 'IS': 'Campano (CAM)', # CB = Campobasso (Capracotta)
    # CALABRIA E BASILICATA (CAL)
    'CZ': 'Calabro Lucano (CAL)', 'CS': 'Calabro Lucano (CAL)', 'KR': 'Calabro Lucano (CAL)',
    'RC': 'Calabro Lucano (CAL)', 'VV': 'Calabro Lucano (CAL)', 'MT': 'Calabro Lucano (CAL)',
    'PZ': 'Calabro Lucano (CAL)',
    # PUGLIA (PUG)
    'BA': 'Pugliese (PUG)', 'BT': 'Pugliese (PUG)', 'BR': 'Pugliese (PUG)', 'FG': 'Pugliese (PUG)',
    'LE': 'Pugliese (PUG)', 'TA': 'Pugliese (PUG)',
    # SICILIA (SIC)
    'AG': 'Siculo (SIC)', 'CL': 'Siculo (SIC)', 'CT': 'Siculo (SIC)', 'EN': 'Siculo (SIC)',
    'ME': 'Siculo (SIC)', 'PA': 'Siculo (SIC)', 'RG': 'Siculo (SIC)', 'SR': 'Siculo (SIC)',
    'TP': 'Siculo (SIC)',
    # MILITARI
    'GM': 'Gruppi Militari (GM)'
}

def estrai_verita_geografica(item):
    """Basa tutto sulla geografia reale della gara"""
    livello = str(item.get("livello", "")).upper()
    if "WORLD" in livello or "OPA" in livello or "INTERNAZIONAL" in livello:
        return "Internazionale/FIS"

    # 1. Controlliamo se la FISI ci ha fatto la grazia di mettere la targa comitato giusta
    c = str(item.get("codiceComitato", "")).strip().upper()
    if not c: c = str(item.get("comitato", "")).strip().upper()
    if c in MAPPA_COMITATI: 
        return MAPPA_COMITATI[c]

    # 2. CONTROLLO PROVINCIALE ASSOLUTO SULLA SOCIETÀ (Es: CB03, CT12, AO01)
    soc = str(item.get("codiceSocieta", "")).strip().upper()
    if len(soc) >= 2:
        provincia = soc[:2] # Prendiamo le prime due lettere
        if provincia in MAPPA_PROVINCE:
            return MAPPA_PROVINCE[provincia]

    return "Altre / Sconosciuto"

# =====================================================================
# 🗓️ FASE 1: RACCOLTA E SMISTAMENTO GEOGRAFICO
# =====================================================================
def spider_calendari_nazionale():
    print("--- 🚀 FASE 1: DOWNLOAD GLOBALE E SMISTAMENTO GEOGRAFICO SULLE PROVINCE ---", flush=True)
    
    anno_corrente = datetime.datetime.now().year
    mese_corrente = datetime.datetime.now().month
    anno_massimo = anno_corrente + 1 if mese_corrente >= 6 else anno_corrente
    stagioni_da_scaricare = list(range(2020, anno_massimo + 1))
    
    LISTA_NERA = ["ALPINO", "SLALOM", "GIGANTE", "GS", "SUPER G", "DISCESA", "BIATHLON", "SNOWBOARD", "SKICROSS", "FREESTYLE", "ERBA", "SKELETON", "BOB", "JUMP", "SALTO"]
    
    gare_uniche_grezze = {}
    
    # Raccogliamo TUTTE le gare passando per qualche server a caso (tanto sputano tutto)
    for slug_sito in COMITATI_SPAZZOLINI:
        print(f"🌍 Interrogo il nodo {slug_sito} per estrarre gare...", flush=True)
        for anno in stagioni_da_scaricare:
            offset = 0
            limit = 500
            while True:
                params = {"action": "competizioni_get_all", "idStagione": str(anno), "url": f"https://comitati.fisi.org/{slug_sito}/calendario/", "limit": limit, "offset": offset}
                try:
                    r = session.get(BASE_URL_AJAX, params=params, timeout=15)
                    data = r.json()
                    if not data or not isinstance(data, list) or len(data) == 0: break 
                    for item in data:
                        id_comp = str(item.get("idCompetizione"))
                        disciplina = str(item.get("disciplina", "")).upper()
                        nome_gara = str(item.get("nome", "")).upper()
                        if (any(k in disciplina for k in ["FONDO", "LANGLAUF", "NORDICO", "XC"]) or any(k in nome_gara for k in ["FONDO", "LANGLAUF", "NORDICO", "CROSS COUNTRY", "XC"])) and not (any(k in nome_gara for k in LISTA_NERA) or any(k in disciplina for k in LISTA_NERA)):
                            gare_uniche_grezze[id_comp] = item
                    if len(data) < limit: break
                    offset += limit
                except Exception: break 
            time.sleep(0.1)

    print(f"\n📦 Trovate {len(gare_uniche_grezze)} gare uniche. Avvio smistamento geografico...", flush=True)
    
    lista_finale_supabase = []
    
    for id_gara, item in gare_uniche_grezze.items():
        comitato_vero = estrai_verita_geografica(item)
        
        lista_finale_supabase.append({
            "id_gara_fisi": id_gara, 
            "gara_nome": item.get("nome", "Gara Senza Nome"),
            "luogo": item.get("comune", "N/D"), 
            "data_gara": item.get("dataInizio", "N/D"), 
            "comitato": comitato_vero 
        })

    if lista_finale_supabase:
        for i in range(0, len(lista_finale_supabase), 1000):
            pacchetto = lista_finale_supabase[i:i+1000]
            supabase.table("Gare").upsert(pacchetto).execute()
        print(f"\n✅ CAPOLAVORO: {len(lista_finale_supabase)} gare assegnate definitivamente.")
        print("Capracotta è in Campania, Catania è in Sicilia e la Valle d'Aosta riposa al sicuro! 🏔️")
    else:
        print("\n❌ Nessuna gara trovata.", flush=True)

if __name__ == "__main__":
    spider_calendari_nazionale()
