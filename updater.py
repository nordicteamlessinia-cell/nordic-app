import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import datetime
import re
from bs4 import BeautifulSoup
from collections import defaultdict
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
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) GitHubActions/Updater'})

BASE_URL_AJAX = "https://comitati.fisi.org/wp-admin/admin-ajax.php"

# =====================================================================
# 📚 DIZIONARI E MAPPE (Il Cervello dell'Algoritmo)
# =====================================================================
COMITATI_FISI = {
    'trentino': 'Trentino (TN)', 'alto-adige': 'Alto Adige (AA)', 'veneto': 'Veneto (VE)',
    'alpi-centrali': 'Alpi Centrali (AC)', 'alpi-occidentali': 'Alpi Occidentali (AOC)',
    'friuli-venezia-giulia': 'Friuli Venezia Giulia (FVG)', 'appennino-emiliano': 'Appennino Emiliano (CAE)',
    'appennino-toscano': 'Appennino Toscano (CAT)', 'abruzzo': 'Abruzzo (CAB)',
    'lazio-sardegna': 'Lazio e Sardegna (CLS)', 'umbro-marchigiano': 'Umbro Marchigiano (CUM)',
    'campano': 'Campano (CAM)', 'calabro-lucano': 'Calabro Lucano (CAL)',
    'pugliese': 'Pugliese (PUG)', 'siculo': 'Siculo (SIC)',
    'ligure': 'Ligure (LIG)', 'asiva': 'Valdostano (ASIVA)'
}

COMITATI_FISI_REVERSE = {v: k for k, v in COMITATI_FISI.items()}

MAPPA_NOMI_COMITATI = {
    'TRENTINO': 'Trentino (TN)', 'TN': 'Trentino (TN)',
    'ALTO ADIGE': 'Alto Adige (AA)', 'AA': 'Alto Adige (AA)', 'SUDTIROL': 'Alto Adige (AA)', 'BZ': 'Alto Adige (AA)',
    'VENETO': 'Veneto (VE)', 'VE': 'Veneto (VE)',
    'ALPI CENTRALI': 'Alpi Centrali (AC)', 'AC': 'Alpi Centrali (AC)',
    'ALPI OCCIDENTALI': 'Alpi Occidentali (AOC)', 'AOC': 'Alpi Occidentali (AOC)',
    'VALDOSTANO': 'Valdostano (ASIVA)', 'ASIVA': 'Valdostano (ASIVA)', 'VDA': 'Valdostano (ASIVA)',
    'FRIULI VENEZIA GIULIA': 'Friuli Venezia Giulia (FVG)', 'FVG': 'Friuli Venezia Giulia (FVG)',
    'APPENNINO EMILIANO': 'Appennino Emiliano (CAE)', 'CAE': 'Appennino Emiliano (CAE)',
    'APPENNINO TOSCANO': 'Appennino Toscano (CAT)', 'CAT': 'Appennino Toscano (CAT)',
    'ABRUZZO': 'Abruzzo (CAB)', 'CAB': 'Abruzzo (CAB)',
    'LAZIO E SARDEGNA': 'Lazio e Sardegna (CLS)', 'CLS': 'Lazio e Sardegna (CLS)',
    'LIGURE': 'Ligure (LIG)', 'LIG': 'Ligure (LIG)', 'LI': 'Ligure (LIG)',
    'UMBRO MARCHIGIANO': 'Umbro Marchigiano (CUM)', 'CUM': 'Umbro Marchigiano (CUM)',
    'CAMPANO': 'Campano (CAM)', 'CAM': 'Campano (CAM)', 'MOL': 'Campano (CAM)',
    'CALABRO LUCANO': 'Calabro Lucano (CAL)', 'CAL': 'Calabro Lucano (CAL)',
    'PUGLIESE': 'Pugliese (PUG)', 'PUG': 'Pugliese (PUG)',
    'SICULO': 'Siculo (SIC)', 'SIC': 'Siculo (SIC)', 'GM': 'Gruppi Militari (GM)'
}

MAPPA_PROVINCE = {
    'TN': 'Trentino (TN)', 'BZ': 'Alto Adige (AA)', 'AO': 'Valdostano (ASIVA)',
    'AL': 'Alpi Occidentali (AOC)', 'AT': 'Alpi Occidentali (AOC)', 'BI': 'Alpi Occidentali (AOC)',
    'CN': 'Alpi Occidentali (AOC)', 'NO': 'Alpi Occidentali (AOC)', 'TO': 'Alpi Occidentali (AOC)',
    'VB': 'Alpi Occidentali (AOC)', 'VC': 'Alpi Occidentali (AOC)', 'BG': 'Alpi Centrali (AC)', 
    'BS': 'Alpi Centrali (AC)', 'CO': 'Alpi Centrali (AC)', 'CR': 'Alpi Centrali (AC)', 
    'LC': 'Alpi Centrali (AC)', 'LO': 'Alpi Centrali (AC)', 'MN': 'Alpi Centrali (AC)', 
    'MI': 'Alpi Centrali (AC)', 'MB': 'Alpi Centrali (AC)', 'PV': 'Alpi Centrali (AC)', 
    'SO': 'Alpi Centrali (AC)', 'VA': 'Alpi Centrali (AC)', 'BL': 'Veneto (VE)', 
    'PD': 'Veneto (VE)', 'RO': 'Veneto (VE)', 'TV': 'Veneto (VE)', 'VE': 'Veneto (VE)', 
    'VR': 'Veneto (VE)', 'VI': 'Veneto (VE)', 'GO': 'Friuli Venezia Giulia (FVG)', 
    'PN': 'Friuli Venezia Giulia (FVG)', 'TS': 'Friuli Venezia Giulia (FVG)', 
    'UD': 'Friuli Venezia Giulia (FVG)', 'GE': 'Ligure (LIG)', 'IM': 'Ligure (LIG)', 
    'SP': 'Ligure (LIG)', 'SV': 'Ligure (LIG)', 'BO': 'Appennino Emiliano (CAE)', 
    'FE': 'Appennino Emiliano (CAE)', 'FC': 'Appennino Emiliano (CAE)', 'MO': 'Appennino Emiliano (CAE)', 
    'PR': 'Appennino Emiliano (CAE)', 'PC': 'Appennino Emiliano (CAE)', 'RA': 'Appennino Emiliano (CAE)', 
    'RE': 'Appennino Emiliano (CAE)', 'RN': 'Appennino Emiliano (CAE)', 'AR': 'Appennino Toscano (CAT)', 
    'FI': 'Appennino Toscano (CAT)', 'GR': 'Appennino Toscano (CAT)', 'LI': 'Appennino Toscano (CAT)', 
    'LU': 'Appennino Toscano (CAT)', 'MS': 'Appennino Toscano (CAT)', 'PI': 'Appennino Toscano (CAT)', 
    'PT': 'Appennino Toscano (CAT)', 'PO': 'Appennino Toscano (CAT)', 'SI': 'Appennino Toscano (CAT)',
    'PG': 'Umbro Marchigiano (CUM)', 'TR': 'Umbro Marchigiano (CUM)', 'AN': 'Umbro Marchigiano (CUM)',
    'AP': 'Umbro Marchigiano (CUM)', 'FM': 'Umbro Marchigiano (CUM)', 'MC': 'Umbro Marchigiano (CUM)',
    'PU': 'Umbro Marchigiano (CUM)', 'FR': 'Lazio e Sardegna (CLS)', 'LT': 'Lazio e Sardegna (CLS)', 
    'RI': 'Lazio e Sardegna (CLS)', 'RM': 'Lazio e Sardegna (CLS)', 'VT': 'Lazio e Sardegna (CLS)', 
    'CA': 'Lazio e Sardegna (CLS)', 'NU': 'Lazio e Sardegna (CLS)', 'OR': 'Lazio e Sardegna (CLS)', 
    'SS': 'Lazio e Sardegna (CLS)', 'SU': 'Lazio e Sardegna (CLS)', 'CH': 'Abruzzo (CAB)', 
    'AQ': 'Abruzzo (CAB)', 'PE': 'Abruzzo (CAB)', 'TE': 'Abruzzo (CAB)', 'AV': 'Campano (CAM)', 
    'BN': 'Campano (CAM)', 'CE': 'Campano (CAM)', 'NA': 'Campano (CAM)', 'SA': 'Campano (CAM)', 
    'CB': 'Campano (CAM)', 'IS': 'Campano (CAM)', 'CZ': 'Calabro Lucano (CAL)', 
    'CS': 'Calabro Lucano (CAL)', 'KR': 'Calabro Lucano (CAL)', 'RC': 'Calabro Lucano (CAL)', 
    'VV': 'Calabro Lucano (CAL)', 'MT': 'Calabro Lucano (CAL)', 'PZ': 'Calabro Lucano (CAL)',
    'BA': 'Pugliese (PUG)', 'BT': 'Pugliese (PUG)', 'BR': 'Pugliese (PUG)', 'FG': 'Pugliese (PUG)',
    'LE': 'Pugliese (PUG)', 'TA': 'Pugliese (PUG)', 'AG': 'Siculo (SIC)', 'CL': 'Siculo (SIC)', 
    'CT': 'Siculo (SIC)', 'EN': 'Siculo (SIC)', 'ME': 'Siculo (SIC)', 'PA': 'Siculo (SIC)', 
    'RG': 'Siculo (SIC)', 'SR': 'Siculo (SIC)', 'TP': 'Siculo (SIC)'
}

MAPPA_LUOGHI = {
    'CAPRACOTTA': 'Campano (CAM)', 'LAGO LACENO': 'Campano (CAM)', 'CAMPITELLO MATESE': 'Campano (CAM)', 'BAGNOLI IRPINO': 'Campano (CAM)', 'PESCOPENNATARO': 'Campano (CAM)', 'BOJANO': 'Campano (CAM)',
    'NICOLOSI': 'Siculo (SIC)', 'LINGUAGLOSSA': 'Siculo (SIC)', 'PIANO PROVENZANA': 'Siculo (SIC)', 'ETNA': 'Siculo (SIC)', 'MADONIE': 'Siculo (SIC)',
    'COGNE': 'Valdostano (ASIVA)', 'GRESSONEY': 'Valdostano (ASIVA)', 'BRUSSON': 'Valdostano (ASIVA)', 'BIONAZ': 'Valdostano (ASIVA)', 'FLASSIN': 'Valdostano (ASIVA)', 'COURMAYEUR': 'Valdostano (ASIVA)', 'VALSAVARENCHE': 'Valdostano (ASIVA)', 'SAINT BARTHELEMY': 'Valdostano (ASIVA)', 'TORGNON': 'Valdostano (ASIVA)', 'SAINT-OYEN': 'Valdostano (ASIVA)', 'SAINT OYEN': 'Valdostano (ASIVA)', 'VALTOURNENCHE': 'Valdostano (ASIVA)', 'VERRAYES': 'Valdostano (ASIVA)', 'OLLOMONT': 'Valdostano (ASIVA)', 'RHEMES': 'Valdostano (ASIVA)', 'CHAMPORCHER': 'Valdostano (ASIVA)', 'LA THUILE': 'Valdostano (ASIVA)', 'MORGEX': 'Valdostano (ASIVA)', 'FONTAINEMORE': 'Valdostano (ASIVA)', 'AYAS': 'Valdostano (ASIVA)', 'ANTEY': 'Valdostano (ASIVA)',
    'BOSCO CHIESANUOVA': 'Veneto (VE)', 'ROVERE': 'Veneto (VE)', 'ASIAGO': 'Veneto (VE)', 'GALLIO': 'Veneto (VE)', 'CORTINA': 'Veneto (VE)', 'FALCADE': 'Veneto (VE)', 'SAPPADA': 'Veneto (VE)', 'PADOLA': 'Veneto (VE)', 'VAL VISDENDE': 'Veneto (VE)',
    'DOBBIACO': 'Alto Adige (AA)', 'ANTERSELVA': 'Alto Adige (AA)', 'VAL RIDANNA': 'Alto Adige (AA)', 'SESTO': 'Alto Adige (AA)', 'CASIES': 'Alto Adige (AA)', 'SLUDERNO': 'Alto Adige (AA)', 'SARENTINO': 'Alto Adige (AA)', 'CORVARA': 'Alto Adige (AA)', 'LACES': 'Alto Adige (AA)',
    'TESERO': 'Trentino (TN)', 'PASSO CEREDA': 'Trentino (TN)', 'VERMIGLIO': 'Trentino (TN)', 'LAVARONE': 'Trentino (TN)', 'BONDONE': 'Trentino (TN)', 'VAL DI SOLE': 'Trentino (TN)', 'VAL DI FIEMME': 'Trentino (TN)', 'RABBI': 'Trentino (TN)',
    'SCHILPARIO': 'Alpi Centrali (AC)', 'LIVIGNO': 'Alpi Centrali (AC)', 'SANTA CATERINA': 'Alpi Centrali (AC)', 'CHIESA VALMALENCO': 'Alpi Centrali (AC)', 'PASSO SAN PELLEGRINO': 'Alpi Centrali (AC)', 'BORMIO': 'Alpi Centrali (AC)', 'VALDIDENTRO': 'Alpi Centrali (AC)', 'SPIAZZI': 'Alpi Centrali (AC)',
    'FORNI AVOLTRI': 'Friuli Venezia Giulia (FVG)', 'TARVISIO': 'Friuli Venezia Giulia (FVG)', 'PIANCAVALLO': 'Friuli Venezia Giulia (FVG)', 'SUTRIO': 'Friuli Venezia Giulia (FVG)', 'FORNI DI SOPRA': 'Friuli Venezia Giulia (FVG)',
    'PRAGELATO': 'Alpi Occidentali (AOC)', 'ENTRACQUE': 'Alpi Occidentali (AOC)', 'FORMAZZA': 'Alpi Occidentali (AOC)', 'SESTRIERE': 'Alpi Occidentali (AOC)', 'BARDONECCHIA': 'Alpi Occidentali (AOC)', 'VALLE STURA': 'Alpi Occidentali (AOC)', 'CHIUSA PESIO': 'Alpi Occidentali (AOC)', 'MARMORA': 'Alpi Occidentali (AOC)', 'PRALI': 'Alpi Occidentali (AOC)',
    'ROCCARASO': 'Abruzzo (CAB)', 'PESCOCOSTANZO': 'Abruzzo (CAB)', 'OPI': 'Abruzzo (CAB)', 'BARREA': 'Abruzzo (CAB)', 'SCANNO': 'Abruzzo (CAB)', 'CAMPO FELICE': 'Abruzzo (CAB)', 'CAMPO IMPERATORE': 'Abruzzo (CAB)', 'OVINDOLI': 'Abruzzo (CAB)',
    'CAMIGLIATELLO': 'Calabro Lucano (CAL)', 'LORICA': 'Calabro Lucano (CAL)', 'SAN GIOVANNI IN FIORE': 'Calabro Lucano (CAL)', 'CARLOMAGNO': 'Calabro Lucano (CAL)',
    'PIEVEPELAGO': 'Appennino Emiliano (CAE)', 'FRASSINORO': 'Appennino Emiliano (CAE)', 'SCHIA': 'Appennino Emiliano (CAE)', 'PIANDELAGOTTI': 'Appennino Emiliano (CAE)', 'SANT\'ANNAPELAGO': 'Appennino Emiliano (CAE)', 'CERRETO': 'Appennino Emiliano (CAE)',
    'ABETONE': 'Appennino Toscano (CAT)', 'FOSCIANDORA': 'Appennino Toscano (CAT)',
    'BOLOGNOLA': 'Umbro Marchigiano (CUM)', 'SARNANO': 'Umbro Marchigiano (CUM)', 'FORCA CANAPINE': 'Umbro Marchigiano (CUM)'
}

ACRONIMI_FISI = [
    "AA", "AC", "AOC", "CAB", "CAE", "CAL", "CAM", "CAT", "CLS", "CUM",
    "FVG", "LIG", "PUG", "SIC", "TN", "VA", "ASIVA", "VE",
    "GM1", "GM2", "GM3", "GM4", "GM5", "FFOO", "FFGG", "CSCA", "CS", "CC", "AM"
]

FONDO_KEYWORDS = ["FONDO", "SCI DI FONDO", "LANGLAUF", "CROSS COUNTRY", "NORDIC", "NORDICO", "XC"]
LISTA_NERA = ["ALPINO", "SLALOM", "GIGANTE", "GS", "SUPER G", "DISCESA", "BIATHLON", "SNOWBOARD", "SKICROSS", "FREESTYLE", "ERBA", "SKELETON", "BOB", "JUMP", "SALTO"]

# =====================================================================
# ⚙️ FUNZIONI CORE
# =====================================================================
def estrai_comitato_master(item):
    livello = str(item.get("livello", "")).upper()
    if "WORLD" in livello or "OPA" in livello or "INTERNAZIONAL" in livello:
        return "Internazionale/FIS", 0

    c_code = str(item.get("codiceComitato", "")).strip().upper()
    c_name = str(item.get("comitato", "")).strip().upper()
    if c_code in MAPPA_NOMI_COMITATI: return MAPPA_NOMI_COMITATI[c_code], 1
    if c_name in MAPPA_NOMI_COMITATI: return MAPPA_NOMI_COMITATI[c_name], 1

    soc = str(item.get("codiceSocieta", "")).strip().upper()
    pref = re.match(r"^[A-Z]+", soc)
    if pref:
        sigla_soc = pref.group(0)
        if sigla_soc in ["AO", "VA", "VDA", "ASIVA"]: return "Valdostano (ASIVA)", 2
        if sigla_soc in MAPPA_PROVINCE: return MAPPA_PROVINCE[sigla_soc], 2

    luogo = str(item.get("comune", "")).upper()
    for loc, comitato_gps in MAPPA_LUOGHI.items():
        if loc in luogo: return comitato_gps, 3
            
    nome_gara = str(item.get("nome", "")).upper()
    if "VALDOSTAN" in nome_gara or "VAL D'AOSTA" in nome_gara or "ASIVA" in nome_gara: return "Valdostano (ASIVA)", 4
    if "CAMPAN" in nome_gara or "MOLIS" in nome_gara: return "Campano (CAM)", 4
    if "SICIL" in nome_gara or "SICUL" in nome_gara: return "Siculo (SIC)", 4

    return "", 5 

def calcola_stagione_fisi(data_gara):
    try:
        if not data_gara or data_gara == "N/D": return str(datetime.datetime.now().year)
        p = data_gara.split("/")
        if len(p) == 3: return str(int(p[2]) + 1) if int(p[1]) >= 6 else str(p[2])
    except: pass
    return str(datetime.datetime.now().year)

# =====================================================================
# 🚀 UPDATER PRINCIPALE (DELTA LOAD)
# =====================================================================
def esegui_aggiornamento_quotidiano():
    print("--- 🚀 AVVIO UPDATER (DELTA LOAD) ---", flush=True)
    
    anno_corrente = datetime.datetime.now().year
    # Scarica solo le gare della stagione corrente e delle due precedenti (es. 2024, 2025, 2026)
    stagioni_da_scaricare = [anno_corrente - 2, anno_corrente - 1, anno_corrente, anno_corrente + 1]
    
    # ---------------------------------------------------------
    # FASE 1: AGGIORNAMENTO GARE
    # ---------------------------------------------------------
    print(f"\n🌍 Cerco nuove gare (o aggiornamenti) per le stagioni: {stagioni_da_scaricare}", flush=True)
    gare_salvate = {}
    portale_yield = defaultdict(int)
    gare_claims = defaultdict(list)
    
    for slug_sito, portale_nome in COMITATI_FISI.items():
        for anno in stagioni_da_scaricare:
            offset, limit = 0, 500
            while True:
                params = {
                    "action": "competizioni_get_all", "idStagione": str(anno),
                    "url": f"https://comitati.fisi.org/{slug_sito}/calendario/", 
                    "limit": limit, "offset": offset
                }
                try:
                    r = session.get(BASE_URL_AJAX, params=params, timeout=15)
                    data = r.json()
                    if not data or not isinstance(data, list) or len(data) == 0: break 
                        
                    for item in data:
                        id_comp = str(item.get("idCompetizione"))
                        portale_yield[portale_nome] += 1
                        
                        disciplina = str(item.get("disciplina", "")).upper()
                        nome_gara = str(item.get("nome", "")).upper()
                        
                        is_fondo = any(k in disciplina for k in FONDO_KEYWORDS) or any(k in nome_gara for k in FONDO_KEYWORDS)
                        is_proibita = any(k in nome_gara for k in LISTA_NERA) or any(k in disciplina for k in LISTA_NERA)
                        
                        if is_fondo and not is_proibita:
                            gare_claims[id_comp].append(portale_nome)
                            comitato_vero, score_affidabilita = estrai_comitato_master(item)
                            
                            if id_comp in gare_salvate:
                                if score_affidabilita < gare_salvate[id_comp]["score"]:
                                    gare_salvate[id_comp]["comitato"] = comitato_vero
                                    gare_salvate[id_comp]["score"] = score_affidabilita
                            else:
                                gare_salvate[id_comp] = {
                                    "id_gara_fisi": id_comp, "gara_nome": item.get("nome", "Gara Senza Nome"),
                                    "luogo": item.get("comune", "N/D"), "data_gara": item.get("dataInizio", "N/D"), 
                                    "comitato": comitato_vero, "disciplina": item.get("disciplina", "N/D"), 
                                    "codice_societa": item.get("codiceSocieta", ""), "codice_comitato": item.get("codiceComitato", ""), 
                                    "score": score_affidabilita
                                }
                    if len(data) < limit: break
                    offset += limit
                except Exception: break 
            time.sleep(0.1)

    lista_finale_supabase = []
    for id_gara, record in gare_salvate.items():
        if record["score"] == 5:
            claims = gare_claims[id_gara]
            best_portal = min(claims, key=lambda p: portale_yield[p])
            if portale_yield[best_portal] > 10000: record["comitato"] = "Altre / Non Assegnate"
            else: record["comitato"] = best_portal

        lista_finale_supabase.append({
            "id_gara_fisi": record["id_gara_fisi"], "gara_nome": record["gara_nome"],
            "luogo": record["luogo"], "data_gara": record["data_gara"], "comitato": record["comitato"],
            "disciplina": record["disciplina"], "codice_societa": record["codice_societa"], 
            "codice_comitato": record["codice_comitato"]
        })

    if lista_finale_supabase:
        for i in range(0, len(lista_finale_supabase), 1000):
            pacchetto = lista_finale_supabase[i:i+1000]
            supabase.table("Gare").upsert(pacchetto).execute()
        print(f"   ✅ Database Gare sincronizzato con {len(lista_finale_supabase)} eventi recenti.", flush=True)

    # ---------------------------------------------------------
    # FASE 2: AGGIORNAMENTO ATLETI E CLASSIFICHE
    # ---------------------------------------------------------
    print("\n⛷️ Controllo se le gare recenti hanno pubblicato i risultati in HTML...", flush=True)
    
    # Processiamo solo le gare appena estratte (ultimi anni) invece di ripescarle tutte dal database
    for gara in lista_finale_supabase:
        id_comp = gara.get('id_gara_fisi')
        nome_g = gara.get('gara_nome')
        data_g = gara.get('data_gara')
        luogo_g = gara.get('luogo')
        nome_comitato_gara = gara.get('comitato')
        
        # Saltiamo le gare sconosciute o internazionali per le quali l'HTML locale spesso fallisce
        if non_assegnata := "Altre / Non Assegnate" in nome_comitato_gara: continue
        
        # 1. Questa gara ha già la classifica nel database?
        controllo_db = supabase.table("Risultati").select("id_comp_collegata").eq("id_comp_collegata", id_comp).limit(1).execute()
        if len(controllo_db.data) > 0:
            continue # Se c'è già, la saltiamo!

        # 2. Se è nuova, la raschiamo!
        slug_sito = COMITATI_FISI_REVERSE.get(nome_comitato_gara, 'trentino')
        stagione_fisi = calcola_stagione_fisi(data_g)
        
        url_comp = f"https://comitati.fisi.org/{slug_sito}/competizione/?idComp={id_comp}&d={stagione_fisi}"
        
        try:
            res = session.get(url_comp, timeout=20)
            soup = BeautifulSoup(res.text, 'html.parser')
            links = soup.find_all('a', href=True)
            id_sottogare = list(set([l['href'].split('idGara=')[1].split('&')[0] for l in links if 'idGara=' in l['href']]))
            
            if not id_sottogare:
                continue # Nessun link trovato (la gara si deve ancora correre o non hanno caricato l'HTML)

            print(f"   🟢 Nuovi Risultati per: {nome_g} ({data_g})", flush=True)
            
            for id_g in id_sottogare:
                url_gara = f"https://comitati.fisi.org/{slug_sito}/gara/?idGara={id_g}&idComp={id_comp}&d={stagione_fisi}"
                r_data = session.get(url_gara, timeout=20)
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
                        blocco_atleta = testi_atleti[i:i+8]
                        comitato_vero_atleta = "N/D"
                        
                        # Lo Scanner degli Acronimi (Il vero comitato dell'atleta)
                        for testo in blocco_atleta:
                            if testo.upper() in ACRONIMI_FISI:
                                comitato_vero_atleta = testo.upper()
                                break
                        
                        batch_atleti.append({
                            "id_gara_fisi": id_g, "id_comp_collegata": id_comp, "posizione": int(testi_atleti[i]),
                            "atleta_nome": testi_atleti[i+2], "societa": testi_atleti[i+4], "tempo": testi_atleti[i+5], 
                            "categoria": categoria_finale, "gara_nome": nome_g, "luogo": luogo_g,
                            "data_gara": data_g, "comitato": comitato_vero_atleta
                        })
                        i += 8
                    else:
                        i += 1
                
                if batch_atleti:
                    supabase.table("Risultati").upsert(batch_atleti).execute()
                    print(f"      ✅ Inseriti {len(batch_atleti)} atleti per la cat: {categoria_finale}", flush=True)
                
                time.sleep(0.3)

        except Exception as e:
            pass

    print("\n✅ UPDATER COMPLETATO CON SUCCESSO! Database allineato alle ultime novità FISI.")

if __name__ == "__main__":
    esegui_aggiornamento_quotidiano()
