import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import datetime
from supabase import create_client
from collections import defaultdict

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

COMITATI_FISI = {
    'Trentino (TN)': 'trentino',
    'Alto Adige (AA)': 'alto-adige',           
    'Veneto (VE)': 'veneto',
    'Alpi Centrali (AC)': 'alpi-centrali',     
    'Alpi Occidentali (AOC)': 'alpi-occidentali', 
    'Valdostano (ASIVA)': 'asiva',
    'Friuli Venezia Giulia (FVG)': 'friuli-venezia-giulia', 
    'Appennino Emiliano (CAE)': 'appennino-emiliano', 
    'Appennino Toscano (CAT)': 'appennino-toscano',   
    'Abruzzo (CAB)': 'abruzzo',
    'Lazio e Sardegna (CLS)': 'lazio-sardegna',
    'Ligure (LIG)': 'ligure',
    'Umbro Marchigiano (CUM)': 'umbro-marchigiano',
    'Campano (CAM)': 'campano',
    'Calabro Lucano (CAL)': 'calabro-lucano',
    'Pugliese (PUG)': 'pugliese',
    'Siculo (SIC)': 'siculo',
}

# =====================================================================
# 🗓️ FASE 1: DOWNLOAD E TRIBUNALE DELLE GARE
# =====================================================================
def spider_calendari_nazionale():
    print("--- 🚀 FASE 1: DOWNLOAD GLOBALE E TRIBUNALE DELLE GARE ---", flush=True)
    
    anno_corrente = datetime.datetime.now().year
    mese_corrente = datetime.datetime.now().month
    anno_massimo = anno_corrente + 1 if mese_corrente >= 6 else anno_corrente
    stagioni_da_scaricare = list(range(2020, anno_massimo + 1))
    
    LISTA_NERA = ["ALPINO", "SLALOM", "GIGANTE", "GS", "SUPER G", "DISCESA", "BIATHLON", "SNOWBOARD", "SKICROSS", "FREESTYLE", "ERBA", "SKELETON", "BOB", "JUMP", "SALTO"]
    
    # 🧠 LE MENTI DELL'ALGORITMO
    reclamazioni = defaultdict(list)    # Tiene traccia di chi reclama cosa: {"id_123": ["Veneto", "Valdostano"]}
    conteggio_comitato = defaultdict(int) # Conta quanto è grande il bottino di ogni comitato (per scovare chi ha il filtro rotto)
    gare_dati = {} # Salva i dati grezzi della gara per usarli dopo
    
    # --- 1. FASE DI DOWNLOAD (Ognuno prende quello che gli dà il server) ---
    for nome_comitato, slug_sito in COMITATI_FISI.items():
        print(f"\n🌍 Scarico calendario da: {nome_comitato}...", flush=True)
        
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
                            # Registriamo la reclamazione!
                            if nome_comitato not in reclamazioni[id_comp]:
                                reclamazioni[id_comp].append(nome_comitato)
                                conteggio_comitato[nome_comitato] += 1
                                gare_dati[id_comp] = item # Salviamo i dati nel cassetto
                                
                    if len(data) < limit: break
                    offset += limit
                    
                except Exception:
                    break 
            
            time.sleep(0.1)

    # --- 2. IL TRIBUNALE (Risoluzione dei conflitti) ---
    print("\n⚖️ IL TRIBUNALE È APERTO: Risoluzione dei furti tra comitati in corso...", flush=True)
    all_gare_fondo = []
    conflitti_risolti = 0
    
    for id_gara, comitati_reclamanti in reclamazioni.items():
        data = gare_dati[id_gara]
        
        # Eccezione: Le gare Mondiali non si discutono, sono Internazionali.
        livello = str(data.get("livello", "")).upper()
        if "WORLD" in livello or "OPA" in livello or "INTERNAZIONAL" in livello:
            vincitore = "Internazionale/FIS"
        else:
            if len(comitati_reclamanti) > 1:
                conflitti_risolti += 1
            # 🏆 LA MAGIA: Vince chi ha il calendario più piccolo! (Filtro funzionante batte Filtro rotto)
            vincitore = min(comitati_reclamanti, key=lambda c: conteggio_comitato[c])
            
        record = {
            "id_gara_fisi": id_gara, 
            "gara_nome": data.get("nome", "Gara Senza Nome"),
            "luogo": data.get("comune", "N/D"), 
            "data_gara": data.get("dataInizio", "N/D"), 
            "comitato": vincitore 
        }
        all_gare_fondo.append(record)

    # --- 3. SALVATAGGIO ---
    if all_gare_fondo:
        for i in range(0, len(all_gare_fondo), 1000):
            pacchetto = all_gare_fondo[i:i+1000]
            supabase.table("Gare").upsert(pacchetto).execute()
        print(f"\n✅ TRIONFO: Salvate {len(all_gare_fondo)} gare uniche. Risolti {conflitti_risolti} conflitti di assegnazione!", flush=True)
    else:
        print("\n❌ Nessuna gara salvata.", flush=True)

if __name__ == "__main__":
    spider_calendari_nazionale()
    # spider_atleti_master() <-- SBLOCCAMI DOPO IL TEST!
