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

# 🥇 LA MAPPA DELLE TARGHE PROVINCIALI (Infallibile)
PROVINCE_COMITATI = {
    # Valdostano (ASIVA)
    'AO': 'Valdostano (ASIVA)', 'AS': 'Valdostano (ASIVA)',
    # Piemonte (AOC)
    'TO': 'Alpi Occidentali (AOC)', 'CN': 'Alpi Occidentali (AOC)', 'BI': 'Alpi Occidentali (AOC)', 
    'VC': 'Alpi Occidentali (AOC)', 'NO': 'Alpi Occidentali (AOC)', 'AL': 'Alpi Occidentali (AOC)', 
    'AT': 'Alpi Occidentali (AOC)', 'VB': 'Alpi Occidentali (AOC)',
    # Lombardia (AC)
    'MI': 'Alpi Centrali (AC)', 'BS': 'Alpi Centrali (AC)', 'BG': 'Alpi Centrali (AC)', 
    'SO': 'Alpi Centrali (AC)', 'LC': 'Alpi Centrali (AC)', 'CO': 'Alpi Centrali (AC)', 
    'VA': 'Alpi Centrali (AC)', 'MB': 'Alpi Centrali (AC)', 'PV': 'Alpi Centrali (AC)', 
    'CR': 'Alpi Centrali (AC)', 'LO': 'Alpi Centrali (AC)', 'MN': 'Alpi Centrali (AC)',
    # Trentino / Alto Adige
    'TN': 'Trentino (TN)', 'BZ': 'Alto Adige (AA)',
    # Veneto (VE)
    'VR': 'Veneto (VE)', 'VI': 'Veneto (VE)', 'BL': 'Veneto (VE)', 'TV': 'Veneto (VE)', 
    'VE': 'Veneto (VE)', 'PD': 'Veneto (VE)', 'RO': 'Veneto (VE)',
    # Friuli (FVG)
    'UD': 'Friuli Venezia Giulia (FVG)', 'PN': 'Friuli Venezia Giulia (FVG)', 
    'TS': 'Friuli Venezia Giulia (FVG)', 'GO': 'Friuli Venezia Giulia (FVG)',
    # Liguria (LIG)
    'GE': 'Ligure (LIG)', 'SV': 'Ligure (LIG)', 'IM': 'Ligure (LIG)', 'SP': 'Ligure (LIG)',
    # Emilia Romagna (CAE)
    'BO': 'Appennino Emiliano (CAE)', 'MO': 'Appennino Emiliano (CAE)', 'RE': 'Appennino Emiliano (CAE)', 
    'PR': 'Appennino Emiliano (CAE)', 'PC': 'Appennino Emiliano (CAE)', 'FE': 'Appennino Emiliano (CAE)', 
    'RA': 'Appennino Emiliano (CAE)', 'FC': 'Appennino Emiliano (CAE)', 'RN': 'Appennino Emiliano (CAE)',
    # Toscana (CAT)
    'FI': 'Appennino Toscano (CAT)', 'AR': 'Appennino Toscano (CAT)', 'SI': 'Appennino Toscano (CAT)', 
    'LU': 'Appennino Toscano (CAT)', 'PT': 'Appennino Toscano (CAT)', 'PO': 'Appennino Toscano (CAT)', 
    'MS': 'Appennino Toscano (CAT)', 'PI': 'Appennino Toscano (CAT)', 'LI': 'Appennino Toscano (CAT)', 'GR': 'Appennino Toscano (CAT)',
    # Umbria & Marche (CUM)
    'PG': 'Umbro Marchigiano (CUM)', 'TR': 'Umbro Marchigiano (CUM)', 'AN': 'Umbro Marchigiano (CUM)', 
    'PU': 'Umbro Marchigiano (CUM)', 'MC': 'Umbro Marchigiano (CUM)', 'AP': 'Umbro Marchigiano (CUM)', 'FM': 'Umbro Marchigiano (CUM)',
    # Lazio & Sardegna (CLS)
    'RM': 'Lazio e Sardegna (CLS)', 'RI': 'Lazio e Sardegna (CLS)', 'VT': 'Lazio e Sardegna (CLS)', 
    'FR': 'Lazio e Sardegna (CLS)', 'LT': 'Lazio e Sardegna (CLS)', 'CA': 'Lazio e Sardegna (CLS)', 
    'SS': 'Lazio e Sardegna (CLS)', 'NU': 'Lazio e Sardegna (CLS)', 'OR': 'Lazio e Sardegna (CLS)', 'SU': 'Lazio e Sardegna (CLS)',
    # Abruzzo (CAB)
    'AQ': 'Abruzzo (CAB)', 'TE': 'Abruzzo (CAB)', 'PE': 'Abruzzo (CAB)', 'CH': 'Abruzzo (CAB)',
    # Campania & Molise (CAM)
    'NA': 'Campano (CAM)', 'SA': 'Campano (CAM)', 'AV': 'Campano (CAM)', 'BN': 'Campano (CAM)', 
    'CE': 'Campano (CAM)', 'CB': 'Campano (CAM)', 'IS': 'Campano (CAM)',
    # Puglia (PUG)
    'BA': 'Pugliese (PUG)', 'FG': 'Pugliese (PUG)', 'LE': 'Pugliese (PUG)', 'TA': 'Pugliese (PUG)', 'BR': 'Pugliese (PUG)', 'BT': 'Pugliese (PUG)',
    # Calabria & Basilicata (CAL)
    'CS': 'Calabro Lucano (CAL)', 'CZ': 'Calabro Lucano (CAL)', 'KR': 'Calabro Lucano (CAL)', 
    'VV': 'Calabro Lucano (CAL)', 'RC': 'Calabro Lucano (CAL)', 'PZ': 'Calabro Lucano (CAL)', 'MT': 'Calabro Lucano (CAL)',
    # Sicilia (SIC)
    'PA': 'Siculo (SIC)', 'CT': 'Siculo (SIC)', 'ME': 'Siculo (SIC)', 'SR': 'Siculo (SIC)', 
    'RG': 'Siculo (SIC)', 'EN': 'Siculo (SIC)', 'CL': 'Siculo (SIC)', 'AG': 'Siculo (SIC)', 'TP': 'Siculo (SIC)',
    # Militari
    'GM': 'Gruppi Militari (GM)'
}

SIGLE_DIRETTE = {
    'AA': 'Alto Adige (AA)', 'AC': 'Alpi Centrali (AC)', 'AOC': 'Alpi Occidentali (AOC)',
    'ASIVA': 'Valdostano (ASIVA)', 'CAB': 'Abruzzo (CAB)', 'CAE': 'Appennino Emiliano (CAE)',
    'CAL': 'Calabro Lucano (CAL)', 'CAM': 'Campano (CAM)', 'CAT': 'Appennino Toscano (CAT)',
    'CLS': 'Lazio e Sardegna (CLS)', 'CUM': 'Umbro Marchigiano (CUM)', 'FVG': 'Friuli Venezia Giulia (FVG)',
    'LIG': 'Ligure (LIG)', 'PUG': 'Pugliese (PUG)', 'SIC': 'Siculo (SIC)', 'TN': 'Trentino (TN)', 'VE': 'Veneto (VE)'
}

def leggi_targa_vera(item):
    """Estrazione chirurgica basata sulle Province e sulle Sigle ufficiali"""
    livello = str(item.get("livello", "")).upper()
    if "WORLD" in livello or "OPA" in livello or "INTERNAZIONAL" in livello:
        return "Internazionale/FIS"

    # 1. Controllo Targa Società (Es: CT012 -> CT -> Siculo)
    soc = str(item.get("codiceSocieta", "")).strip().upper()
    if len(soc) >= 2:
        prime_due = soc[:2]
        if prime_due in PROVINCE_COMITATI:
            return PROVINCE_COMITATI[prime_due]
        
    # 2. Controllo Sigla Comitato dichiarata
    c = str(item.get("codiceComitato", "")).strip().upper()
    if not c: c = str(item.get("comitato", "")).strip().upper()
    if c in SIGLE_DIRETTE: return SIGLE_DIRETTE[c]

    # 3. Non Assegnabile (evita che inquini altri comitati)
    return "Varie / Non Assegnate"

# =====================================================================
# 🗓️ FASE 1: DOWNLOAD MASSIVO E SMISTAMENTO PER TARGA
# =====================================================================
def spider_calendari_nazionale():
    print("--- 🚀 FASE 1: RACCOLTA GLOBALE E SMISTAMENTO TARGHE PROVINCIALI ---", flush=True)
    
    anno_corrente = datetime.datetime.now().year
    mese_corrente = datetime.datetime.now().month
    anno_massimo = anno_corrente + 1 if mese_corrente >= 6 else anno_corrente
    stagioni_da_scaricare = list(range(2020, anno_massimo + 1))
    
    LISTA_NERA = ["ALPINO", "SLALOM", "GIGANTE", "GS", "SUPER G", "DISCESA", "BIATHLON", "SNOWBOARD", "SKICROSS", "FREESTYLE", "ERBA", "SKELETON", "BOB", "JUMP", "SALTO"]
    
    gare_uniche = {} 
    
    comitati_da_interrogare = [
        'trentino', 'alto-adige', 'veneto', 'alpi-centrali', 'alpi-occidentali', 
        'asiva', 'friuli-venezia-giulia', 'appennino-emiliano', 'appennino-toscano',   
        'abruzzo', 'lazio-sardegna', 'ligure', 'umbro-marchigiano', 'campano',
        'calabro-lucano', 'pugliese', 'siculo'
    ]
    
    print("\n🌍 Sto spazzolando l'intera rete FISI per raccogliere le gare...", flush=True)
    
    # Raccogliamo in modo brutale TUTTO quello che i server restituiscono
    for slug in comitati_da_interrogare:
        for anno in stagioni_da_scaricare:
            offset = 0
            limit = 200
            
            while True:
                params = {"action": "competizioni_get_all", "idStagione": str(anno), "url": f"https://comitati.fisi.org/{slug}/calendario/", "limit": limit, "offset": offset}
                try:
                    r = session.get(BASE_URL_AJAX, params=params, timeout=10)
                    data = r.json()
                    if not data or not isinstance(data, list) or len(data) == 0: break 
                        
                    for item in data:
                        id_comp = str(item.get("idCompetizione"))
                        disciplina = str(item.get("disciplina", "")).upper()
                        nome_gara = str(item.get("nome", "")).upper()
                        
                        is_fondo = any(k in disciplina for k in ["FONDO", "LANGLAUF", "NORDICO", "XC"]) or any(k in nome_gara for k in ["FONDO", "LANGLAUF", "NORDICO", "CROSS COUNTRY", "XC"])
                        is_proibita = any(k in nome_gara for k in LISTA_NERA) or any(k in disciplina for k in LISTA_NERA)
                        
                        if is_fondo and not is_proibita:
                            gare_uniche[id_comp] = item # La inserisce/sovrascrive pulendo i doppioni
                            
                    if len(data) < limit: break
                    offset += limit
                except Exception:
                    break 

    print(f"📦 Raccolta terminata: trovate {len(gare_uniche)} gare uniche. Inizio lo smistamento per targhe...", flush=True)

    # Smistiamo le gare leggendo la targa
    all_gare_fondo = []
    for id_gara, item in gare_uniche.items():
        comitato_vero = leggi_targa_vera(item)
        
        record = {
            "id_gara_fisi": id_gara, 
            "gara_nome": item.get("nome", "Gara Senza Nome"),
            "luogo": item.get("comune", "N/D"), 
            "data_gara": item.get("dataInizio", "N/D"), 
            "comitato": comitato_vero 
        }
        all_gare_fondo.append(record)

    # Salvataggio
    if all_gare_fondo:
        for i in range(0, len(all_gare_fondo), 1000):
            pacchetto = all_gare_fondo[i:i+1000]
            supabase.table("Gare").upsert(pacchetto).execute()
        print(f"\n✅ TRIONFO: Salvate {len(all_gare_fondo)} gare con assegnazione perfetta basata sulla provincia!", flush=True)
    else:
        print("\n❌ Nessuna gara salvata.", flush=True)

if __name__ == "__main__":
    spider_calendari_nazionale()
    # spider_atleti_master() <-- Disattivata per il test veloce
