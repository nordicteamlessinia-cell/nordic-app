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
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})

BASE_URL_AJAX = "https://comitati.fisi.org/wp-admin/admin-ajax.php"

# 🥇 CORRIERI PER IL DOWNLOAD
COMITATI_FISI = [
    'trentino', 'alto-adige', 'veneto', 'alpi-centrali', 'alpi-occidentali', 
    'asiva', 'friuli-venezia-giulia', 'appennino-emiliano', 'appennino-toscano',   
    'abruzzo', 'lazio-sardegna', 'ligure', 'umbro-marchigiano', 'campano',
    'calabro-lucano', 'pugliese', 'siculo'
]

# 🎯 IL LETTORE DI CARTE D'IDENTITÀ (Legge il JSON puro)
MAPPA_SIGLE = {
    'AA': 'Alto Adige (AA)', 'AC': 'Alpi Centrali (AC)', 'AOC': 'Alpi Occidentali (AOC)',
    'ASIVA': 'Valdostano (ASIVA)', 'VA': 'Valdostano (ASIVA)',
    'CAB': 'Abruzzo (CAB)', 'CAE': 'Appennino Emiliano (CAE)', 'CAL': 'Calabro Lucano (CAL)',
    'CAM': 'Campano (CAM)', 'MOL': 'Campano (CAM)', # Molise unito alla Campania
    'CAT': 'Appennino Toscano (CAT)', 'CLS': 'Lazio e Sardegna (CLS)',
    'CUM': 'Umbro Marchigiano (CUM)', 'FVG': 'Friuli Venezia Giulia (FVG)',
    'LIG': 'Ligure (LIG)', 'PUG': 'Pugliese (PUG)', 'SIC': 'Siculo (SIC)',
    'TN': 'Trentino (TN)', 'VE': 'Veneto (VE)', 'GM': 'Gruppi Militari (GM)'
}

def estrai_verita_assoluta(item):
    """Ignora chi ci ha mandato i dati e legge la targa originale della gara"""
    livello = str(item.get("livello", "")).upper()
    if "WORLD" in livello or "OPA" in livello or "INTERNAZIONAL" in livello:
        return "Internazionale/FIS"

    # 1. Targa Comitato ufficiale
    sigla = str(item.get("codiceComitato", "")).strip().upper()
    if not sigla: sigla = str(item.get("comitato", "")).strip().upper()
    if sigla in MAPPA_SIGLE: return MAPPA_SIGLE[sigla]

    # 2. Targa Società (Es: SIC0123 -> SIC = Sicilia)
    soc = str(item.get("codiceSocieta", "")).strip().upper()
    for s in sorted(MAPPA_SIGLE.keys(), key=len, reverse=True):
        if soc.startswith(s): return MAPPA_SIGLE[s]

    # 3. Se non c'è targa (rarissimo), marchiamo come Varie
    return "Altre / Non Assegnate"

# =====================================================================
# 🗓️ FASE 1: DOWNLOAD GLOBALE E LETTURA DEL DNA
# =====================================================================
def spider_calendari_nazionale():
    print("--- 🚀 FASE 1: DOWNLOAD MASSIVO E SMISTAMENTO TARGHE ---", flush=True)
    
    anno_corrente = datetime.datetime.now().year
    mese_corrente = datetime.datetime.now().month
    anno_massimo = anno_corrente + 1 if mese_corrente >= 6 else anno_corrente
    stagioni_da_scaricare = list(range(2020, anno_massimo + 1))
    
    LISTA_NERA = ["ALPINO", "SLALOM", "GIGANTE", "GS", "SUPER G", "DISCESA", "BIATHLON", "SNOWBOARD", "SKICROSS", "FREESTYLE", "ERBA", "SKELETON", "BOB", "JUMP", "SALTO"]
    
    gare_uniche_grezze = {} # Qui buttiamo tutte le gare estratte per non avere doppioni
    
    print("🌍 Sto spazzolando tutti i server d'Italia...", flush=True)
    
    # 1. FASE DI RACCOLTA (Prendiamo tutto quello che ci danno)
    for slug_sito in COMITATI_FISI:
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
                            # Salviamo la gara grezza (sovrascrive eventuali doppioni automaticamente)
                            gare_uniche_grezze[id_comp] = item
                                
                    if len(data) < limit: break
                    offset += limit
                    
                except Exception:
                    break 
                    
    print(f"📦 Raccolta finita. Trovate {len(gare_uniche_grezze)} gare di Fondo uniche in tutta Italia.", flush=True)
    print("🔍 Inizio lettura delle targhe (DNA) per l'assegnazione regionale...", flush=True)

    # 2. FASE DI ASSEGNAZIONE CHIRURGICA
    all_gare_fondo = []
    
    for id_gara, item_grezzo in gare_uniche_grezze.items():
        # ESTRAIAMO IL VERO COMITATO GUARDANDO IL CODICE INTERNO
        comitato_vero = estrai_verita_assoluta(item_grezzo)
        
        record = {
            "id_gara_fisi": id_gara, 
            "gara_nome": item_grezzo.get("nome", "Gara Senza Nome"),
            "luogo": item_grezzo.get("comune", "N/D"), 
            "data_gara": item_grezzo.get("dataInizio", "N/D"), 
            "comitato": comitato_vero 
        }
        all_gare_fondo.append(record)

    # 3. SALVATAGGIO NEL DATABASE
    if all_gare_fondo:
        for i in range(0, len(all_gare_fondo), 1000):
            pacchetto = all_gare_fondo[i:i+1000]
            supabase.table("Gare").upsert(pacchetto).execute()
        print(f"\n✅ TRIONFO: Salvate {len(all_gare_fondo)} gare! Capracotta è tornata al Sud e l'Etna in Sicilia!", flush=True)
    else:
        print("\n❌ Nessuna gara salvata.", flush=True)

if __name__ == "__main__":
    spider_calendari_nazionale()
    # spider_atleti_master() <-- Disattivata per il test
