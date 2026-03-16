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

# 🥇 LA FILA INDIANA: ASIVA è rigorosamente per ultima per non rubare nulla
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
    'asiva': 'Valdostano (ASIVA)' # <-- IN PUNIZIONE IN FONDO ALLA FILA
}

# 🎯 IL DECODER DEL DNA
MAPPA_SIGLE = {
    'AA': 'Alto Adige (AA)', 'AC': 'Alpi Centrali (AC)', 'AOC': 'Alpi Occidentali (AOC)',
    'ASIVA': 'Valdostano (ASIVA)', 'VA': 'Valdostano (ASIVA)', 'CAB': 'Abruzzo (CAB)',
    'CAE': 'Appennino Emiliano (CAE)', 'CAL': 'Calabro Lucano (CAL)', 'CAM': 'Campano (CAM)',
    'MOL': 'Campano (CAM)', 'CAT': 'Appennino Toscano (CAT)', 'CLS': 'Lazio e Sardegna (CLS)',
    'CUM': 'Umbro Marchigiano (CUM)', 'FVG': 'Friuli Venezia Giulia (FVG)', 'LIG': 'Ligure (LIG)', 
    'PUG': 'Pugliese (PUG)', 'SIC': 'Siculo (SIC)', 'TN': 'Trentino (TN)', 'VE': 'Veneto (VE)', 
    'GM': 'Gruppi Militari (GM)'
}

def estrai_comitato(item, fallback_nome):
    """Restituisce il Nome del Comitato e un True/False se l'ha trovato col DNA o a caso"""
    livello = str(item.get("livello", "")).upper()
    if "WORLD" in livello or "OPA" in livello or "INTERNAZIONAL" in livello:
        return "Internazionale/FIS", True

    c1 = str(item.get("codiceComitato", "")).strip().upper()
    c2 = str(item.get("comitato", "")).strip().upper()

    if c1 in MAPPA_SIGLE: return MAPPA_SIGLE[c1], True
    if c2 in MAPPA_SIGLE: return MAPPA_SIGLE[c2], True

    soc = str(item.get("codiceSocieta", "")).strip().upper()
    for sigla in sorted(MAPPA_SIGLE.keys(), key=len, reverse=True):
        if soc.startswith(sigla): return MAPPA_SIGLE[sigla], True

    # Se la gara non ha targa, usiamo il nome del comitato alla cui porta abbiamo bussato
    return fallback_nome, False

# =====================================================================
# 🗓️ FASE 1: L'ALGORITMO IBRIDO
# =====================================================================
def spider_calendari_nazionale():
    print("--- 🚀 FASE 1: DOWNLOAD MASSIVO E ASSEGNAZIONE IBRIDA ---", flush=True)
    
    anno_corrente = datetime.datetime.now().year
    mese_corrente = datetime.datetime.now().month
    anno_massimo = anno_corrente + 1 if mese_corrente >= 6 else anno_corrente
    stagioni_da_scaricare = list(range(2020, anno_massimo + 1))
    
    LISTA_NERA = ["ALPINO", "SLALOM", "GIGANTE", "GS", "SUPER G", "DISCESA", "BIATHLON", "SNOWBOARD", "SKICROSS", "FREESTYLE", "ERBA", "SKELETON", "BOB", "JUMP", "SALTO"]
    
    gare_salvate = {} # Dizionario per evitare doppioni
    assegnate_dna = 0
    assegnate_porta = 0
    
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
                            comitato_vero, has_dna = estrai_comitato(item, nome_comitato_fallback)
                            
                            # Logica Anti-Furto: 
                            # Se avevamo già salvato questa gara, la sovrascriviamo SOLO SE prima non avevamo il DNA e ora sì.
                            if id_comp in gare_salvate:
                                if has_dna and not gare_salvate[id_comp]["has_dna"]:
                                    gare_salvate[id_comp]["comitato"] = comitato_vero
                                    gare_salvate[id_comp]["has_dna"] = True
                            else:
                                if has_dna: assegnate_dna += 1
                                else: assegnate_porta += 1
                                
                                gare_salvate[id_comp] = {
                                    "id_gara_fisi": id_comp, 
                                    "gara_nome": item.get("nome", "Gara Senza Nome"),
                                    "luogo": item.get("comune", "N/D"), 
                                    "data_gara": item.get("dataInizio", "N/D"), 
                                    "comitato": comitato_vero,
                                    "has_dna": has_dna
                                }
                                
                    if len(data) < limit: break
                    offset += limit
                    
                except Exception:
                    break 
            
            time.sleep(0.1)

    # Prepariamo la lista da inviare a Supabase togliendo la variabile 'has_dna'
    lista_finale_supabase = []
    for id_gara, record in gare_salvate.items():
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
        print(f"🧬 Gare assegnate leggendo il DNA esatto: {assegnate_dna}")
        print(f"🚪 Gare assegnate in base al portale interrogato: {assegnate_porta}")
    else:
        print("\n❌ Nessuna gara salvata.", flush=True)

if __name__ == "__main__":
    spider_calendari_nazionale()
    # spider_atleti_master() <-- Sblocca dopo aver controllato
