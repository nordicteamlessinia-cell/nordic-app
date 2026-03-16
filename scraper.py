import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import datetime
import re
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

BASE_URL_AJAX = "https://comitati.import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import datetime
import re
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

BASE_URL_AJAX = "https://comitati.fisi.org/wp-admin/admin-ajax.php"

# 🥇 LA FILA INDIANA
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

# 🎯 DECODER COMITATI 
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

# 🗺️ MAPPA PROVINCE 
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

# 📍 IL GPS INTERNO AGGIORNATO CON LE TUE CORREZIONI
MAPPA_LUOGHI = {
    'CAPRACOTTA': 'Campano (CAM)', 'LAGO LACENO': 'Campano (CAM)', 'CAMPITELLO MATESE': 'Campano (CAM)',
    'NICOLOSI': 'Siculo (SIC)', 'LINGUAGLOSSA': 'Siculo (SIC)', 'PIANO PROVENZANA': 'Siculo (SIC)', 'ETNA': 'Siculo (SIC)',
    'COGNE': 'Valdostano (ASIVA)', 'GRESSONEY': 'Valdostano (ASIVA)', 'BRUSSON': 'Valdostano (ASIVA)', 
    'BIONAZ': 'Valdostano (ASIVA)', 'FLASSIN': 'Valdostano (ASIVA)', 'COURMAYEUR': 'Valdostano (ASIVA)', 
    'VALSAVARENCHE': 'Valdostano (ASIVA)', 'SAINT BARTHELEMY': 'Valdostano (ASIVA)', 'TORGNON': 'Valdostano (ASIVA)',
    'SAINT-OYEN': 'Valdostano (ASIVA)', 'SAINT OYEN': 'Valdostano (ASIVA)', # <-- AGGIUNTO
    'VALTOURNENCHE': 'Valdostano (ASIVA)', 'VERRAYES': 'Valdostano (ASIVA)', # <-- AGGIUNTO
    'BOSCO CHIESANUOVA': 'Veneto (VE)', 'ROVERE': 'Veneto (VE)', 'ASIAGO': 'Veneto (VE)', 'GALLIO': 'Veneto (VE)', 'CORTINA': 'Veneto (VE)',
    'DOBBIACO': 'Alto Adige (AA)', 'ANTERSELVA': 'Alto Adige (AA)', 'VAL RIDANNA': 'Alto Adige (AA)', 'SESTO': 'Alto Adige (AA)',
    'TESERO': 'Trentino (TN)', 'PASSO CEREDA': 'Trentino (TN)', 'VERMIGLIO': 'Trentino (TN)',
    'SCHILPARIO': 'Alpi Centrali (AC)', 'LIVIGNO': 'Alpi Centrali (AC)', 'SANTA CATERINA': 'Alpi Centrali (AC)',
    'FORNI AVOLTRI': 'Friuli Venezia Giulia (FVG)', 'TARVISIO': 'Friuli Venezia Giulia (FVG)', 'PIANCAVALLO': 'Friuli Venezia Giulia (FVG)',
    'PRAGELATO': 'Alpi Occidentali (AOC)', 'ENTRACQUE': 'Alpi Occidentali (AOC)', 'FORMAZZA': 'Alpi Occidentali (AOC)',
    'ROCCARASO': 'Abruzzo (CAB)', 'PESCOCOSTANZO': 'Abruzzo (CAB)', 'OPI': 'Abruzzo (CAB)',
    'CAMIGLIATELLO': 'Calabro Lucano (CAL)', 'LORICA': 'Calabro Lucano (CAL)',
    'PIEVEPELAGO': 'Appennino Emiliano (CAE)', 'FRASSINORO': 'Appennino Emiliano (CAE)', 'SCHIA': 'Appennino Emiliano (CAE)'
}

FONDO_KEYWORDS = ["FONDO", "SCI DI FONDO", "LANGLAUF", "CROSS COUNTRY", "NORDIC", "NORDICO", "XC"]
LISTA_NERA = ["ALPINO", "SLALOM", "GIGANTE", "GS", "SUPER G", "DISCESA", "BIATHLON", "SNOWBOARD", "SKICROSS", "FREESTYLE", "ERBA", "SKELETON", "BOB", "JUMP", "SALTO"]

def estrai_comitato_master(item, fallback_nome):
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
        if sigla_soc in ["AO", "VA", "VDA", "ASIVA"]:
            return "Valdostano (ASIVA)", 2
        if sigla_soc in MAPPA_PROVINCE:
            return MAPPA_PROVINCE[sigla_soc], 2

    luogo = str(item.get("comune", "")).upper()
    for loc, comitato_gps in MAPPA_LUOGHI.items():
        if loc in luogo:
            return comitato_gps, 3
            
    nome_gara = str(item.get("nome", "")).upper()
    if "VALDOSTAN" in nome_gara or "VAL D'AOSTA" in nome_gara or "ASIVA" in nome_gara: return "Valdostano (ASIVA)", 4
    if "CAMPAN" in nome_gara or "MOLIS" in nome_gara: return "Campano (CAM)", 4
    if "SICIL" in nome_gara or "SICUL" in nome_gara: return "Siculo (SIC)", 4

    return fallback_nome, 5

# =====================================================================
# 🗓️ FASE 1: L'ALGORITMO MASTER DEFINITIVO
# =====================================================================
def spider_calendari_nazionale():
    print("--- 🚀 FASE 1: L'ALGORITMO MASTER IN ESECUZIONE ---", flush=True)
    
    anno_corrente = datetime.datetime.now().year
    anno_massimo = anno_corrente + 1 if datetime.datetime.now().month >= 6 else anno_corrente
    stagioni_da_scaricare = list(range(2010, anno_massimo + 1))
    
    gare_salvate = {} 
    statistiche = {0:0, 1:0, 2:0, 3:0, 4:0, 5:0} 
    contatore_scansione = 0
    
    for slug_sito, portale_fallback in COMITATI_FISI.items():
        print(f"\n🌍 Interrogo il portale: {portale_fallback}...", flush=True)
        
        for anno in stagioni_da_scaricare:
            offset = 0
            limit = 500
            
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
                        contatore_scansione += 1
                        id_comp = str(item.get("idCompetizione"))
                        disciplina = str(item.get("disciplina", "")).upper()
                        nome_gara = str(item.get("nome", "")).upper()
                        
                        is_fondo = any(k in disciplina for k in FONDO_KEYWORDS) or \
                                   any(k in nome_gara for k in FONDO_KEYWORDS)
                        is_proibita = any(k in nome_gara for k in LISTA_NERA) or any(k in disciplina for k in LISTA_NERA)
                        
                        if is_fondo and not is_proibita:
                            comitato_vero, score_affidabilita = estrai_comitato_master(item, portale_fallback)
                            
                            if id_comp in gare_salvate:
                                if score_affidabilita < gare_salvate[id_comp]["score"]:
                                    gare_salvate[id_comp]["comitato"] = comitato_vero
                                    gare_salvate[id_comp]["score"] = score_affidabilita
                            else:
                                gare_salvate[id_comp] = {
                                    "id_gara_fisi": id_comp, 
                                    "gara_nome": item.get("nome", "Gara Senza Nome"),
                                    "luogo": item.get("comune", "N/D"), 
                                    "data_gara": item.get("dataInizio", "N/D"), 
                                    "comitato": comitato_vero,
                                    "disciplina": item.get("disciplina", "N/D"), 
                                    "codice_societa": item.get("codiceSocieta", ""), 
                                    "codice_comitato": item.get("codiceComitato", ""), 
                                    "score": score_affidabilita
                                }
                                
                                if len(gare_salvate) % 500 == 0:
                                    print(f"   📈 Gare di fondo raccolte finora: {len(gare_salvate)}")
                                
                    if len(data) < limit: break
                    offset += limit
                    
                except Exception as e:
                    print(f"   ⚠️ Errore API su {slug_sito} ({anno}) a offset {offset}: {e}")
                    break 
            time.sleep(0.1)

    print(f"\n✅ Scansione completata. Analizzate in totale {contatore_scansione} righe dal database FISI.")

    lista_finale_supabase = []
    for id_gara, record in gare_salvate.items():
        statistiche[record["score"]] += 1
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
            
        print(f"\n🏆 DATABASE PERFETTO E BLINDATO DAL 2010!")
        print(f"🏁 {len(lista_finale_supabase)} gare salvate in totale.")
        print(f"\n📊 REPORT AFFIDABILITÀ ASSEGNAZIONI:")
        print(f"   Rank 0 (Internazionali):           {statistiche[0]}")
        print(f"   Rank 1 (Metadato FISI Ufficiale):  {statistiche[1]}")
        print(f"   Rank 2 (Targa Società/Provincia):  {statistiche[2]}")
        print(f"   Rank 3 (GPS / Mappa Luoghi):       {statistiche[3]}")
        print(f"   Rank 4 (Nome Gara):                {statistiche[4]}")
        print(f"   Rank 5 (Fallback Sicurezza):       {statistiche[5]}")
    else:
        print("\n❌ Nessuna gara salvata.", flush=True)

if __name__ == "__main__":
    spider_calendari_nazionale()fisi.org/wp-admin/admin-ajax.php"

# 🥇 LA FILA INDIANA
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

# 🎯 DECODER COMITATI 
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
    'PUGLIESE': 'Pugliese (PUG)', 'PUG': 'Pug
