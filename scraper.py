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

# 🥇 LA FILA INDIANA
COMITATI_FISI = {
    'trentino': 'Trentino (TN)',
    'alto-adige': 'Alto Adige (AA)',
    'veneto': 'Veneto (VE)',
    'alpi-centrali': 'Alpi Centrali (AC)',
    'alpi-occidentali': 'Alpi Occidentali (AOC)',
    'friuli-venezia-giulia': 'Friuli Venezia Giulia (FVG)',
    'appennino-emiliano': 'Appennino Emiliano (CAE)',
    'appennino-toscano': 'Appennino Toscano (CAT)',
    'abruzzo': 'Abruzzo (CAB)',
    'lazio-sardegna': 'Lazio e Sardegna (CLS)',
    'ligure': 'Ligure (LIG)',
    'umbro-marchigiano': 'Umbro Marchigiano (CUM)',
    'campano': 'Campano (CAM)',
    'calabro-lucano': 'Calabro Lucano (CAL)',
    'pugliese': 'Pugliese (PUG)',
    'siculo': 'Siculo (SIC)',
    'asiva': 'Valdostano (ASIVA)'
}

# 🎯 MAPPA SIGLE
MAPPA_SIGLE = {
    'AA': 'Alto Adige (AA)', 'AC': 'Alpi Centrali (AC)', 'AOC': 'Alpi Occidentali (AOC)',
    'ASIVA': 'Valdostano (ASIVA)', 'VA': 'Valdostano (ASIVA)', 'CAB': 'Abruzzo (CAB)',
    'CAE': 'Appennino Emiliano (CAE)', 'CAL': 'Calabro Lucano (CAL)', 'CAM': 'Campano (CAM)',
    'MOL': 'Campano (CAM)', 'CAT': 'Appennino Toscano (CAT)', 'CLS': 'Lazio e Sardegna (CLS)',
    'CUM': 'Umbro Marchigiano (CUM)', 'FVG': 'Friuli Venezia Giulia (FVG)', 'LIG': 'Ligure (LIG)', 
    'PUG': 'Pugliese (PUG)', 'SIC': 'Siculo (SIC)', 'TN': 'Trentino (TN)', 'VE': 'Veneto (VE)', 
    'GM': 'Gruppi Militari (GM)'
}

def estrai_comitato_con_ranking(item, fallback_nome):
    """
    Restituisce (Nome_Comitato, Livello_Affidabilità)
    Livelli (più basso = più affidabile):
    0 = Internazionale (Incontrovertibile)
    1 = codiceComitato esatto
    2 = comitato esatto
    3 = prefisso codiceSocieta
    4 = fallback del portale interrogato
    """
    livello = str(item.get("livello", "")).upper()
    if "WORLD" in livello or "OPA" in livello or "INTERNAZIONAL" in livello:
        return "Internazionale/FIS", 0

    # Rank 1: codiceComitato
    c1 = str(item.get("codiceComitato", "")).strip().upper()
    if c1 in MAPPA_SIGLE: return MAPPA_SIGLE[c1], 1

    # Rank 2: comitato
    c2 = str(item.get("comitato", "")).strip().upper()
    if c2 in MAPPA_SIGLE: return MAPPA_SIGLE[c2], 2

    # Rank 3: prefisso codiceSocieta
    soc = str(item.get("codiceSocieta", "")).strip().upper()
    for sigla in sorted(MAPPA_SIGLE.keys(), key=len, reverse=True):
        if soc.startswith(sigla): return MAPPA_SIGLE[sigla], 3

    # Rank 4: Fallback
    return fallback_nome, 4

# =====================================================================
# 🗓️ FASE 1: DOWNLOAD CON GESTIONE COLLISIONI TRAMITE RANKING
# =====================================================================
def spider_calendari_nazionale():
    print("--- 🚀 FASE 1: DOWNLOAD MASSIVO E RISOLUZIONE COLLISIONI TRAMITE RANKING ---", flush=True)
    
    anno_corrente = datetime.datetime.now().year
    mese_corrente = datetime.datetime.now().month
    anno_massimo = anno_corrente + 1 if mese_corrente >= 6 else anno_corrente
    stagioni_da_scaricare = list(range(2020, anno_massimo + 1))
    
    LISTA_NERA = ["ALPINO", "SLALOM", "GIGANTE", "GS", "SUPER G", "DISCESA", "BIATHLON", "SNOWBOARD", "SKICROSS", "FREESTYLE", "ERBA", "SKELETON", "BOB", "JUMP", "SALTO"]
    
    gare_salvate = {} # key: id_comp, value: dict completo
    statistiche = {0:0, 1:0, 2:0, 3:0, 4:0} # Per vedere da dove arrivano le assegnazioni
    
    for slug_sito, nome_comitato_fallback in COMITATI_FISI.items():
        print(f"\n🌍 Interrogo il portale: {nome_comitato_fallback}...", flush=True)
        
        for anno in stagioni_da_scaricare:
            offset = 0
            limit = 200
            
            while True:
                params = {
                    "action": "competizioni_get_all",
                    "idStagione": str(anno),
                    "url": f"https://comitati.fisi.org/{slug_sito}/calendario/", 
                    "limit": limit,
                    "offset": offset
                }
                
                try:
                    r = session.get(BASE_URL_AJAX, params=params, timeout=15)
                    data = r.json()
                    
                    if not data or not isinstance(data, list) or len(data) == 0:
                        break 
                        
                    for item in data:
                        id_comp = str(item.get("idCompetizione"))
                        disciplina = str(item.get("disciplina", "")).upper()
                        nome_gara = str(item.get("nome", "")).upper()
                        
                        is_fondo = any(k in disciplina for k in ["FONDO", "LANGLAUF", "NORDICO", "XC"]) or \
                                   any(k in nome_gara for k in ["FONDO", "LANGLAUF", "NORDICO", "CROSS COUNTRY", "XC"])
                        is_proibita = any(k in nome_gara for k in LISTA_NERA) or any(k in disciplina for k in LISTA_NERA)
                        
                        if is_fondo and not is_proibita:
                            comitato_vero, score_affidabilita = estrai_comitato_con_ranking(item, nome_comitato_fallback)
                            
                            # Logica Risoluzione Collisioni
                            if id_comp in gare_salvate:
                                # Sovrascrivi SOLO se la nuova informazione è PIÙ affidabile (score minore)
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
                                    "score": score_affidabilita
                                }
                                
                    if len(data) < limit: break
                    offset += limit
                    
                except Exception:
                    break 
            
            time.sleep(0.1)

    # Output e Salvataggio
    lista_finale_supabase = []
    for id_gara, record in gare_salvate.items():
        statistiche[record["score"]] += 1
        lista_finale_supabase.append({
            "id_gara_fisi": record["id_gara_fisi"],
            "gara_nome": record["gara_nome"],
            "luogo": record["luogo"],
            "data_gara": record["data_gara"],
            "comitato": record["comitato"]
        })

    if lista_finale_supabase:
        for i in range(0, len(lista_finale_supabase), 1000):
            pacchetto = lista_finale_supabase[i:i+1000]
            supabase.table("Gare").upsert(pacchetto).execute()
        print(f"\n✅ TRIONFO: {len(lista_finale_supabase)} gare salvate in totale!")
        print(f"📊 REPORT AFFIDABILITÀ ASSEGNAZIONI:")
        print(f"   Rank 0 (Internazionali certe): {statistiche[0]}")
        print(f"   Rank 1 (codiceComitato esatto): {statistiche[1]}")
        print(f"   Rank 2 (comitato esatto): {statistiche[2]}")
        print(f"   Rank 3 (prefisso codiceSocieta): {statistiche[3]}")
        print(f"   Rank 4 (Fallback portale): {statistiche[4]}")
    else:
        print("\n❌ Nessuna gara salvata.", flush=True)

if __name__ == "__main__":
    spider_calendari_nazionale()
    # spider_atleti_master() <-- Togli il commento se i dati sul DB sono finalmente perfetti
