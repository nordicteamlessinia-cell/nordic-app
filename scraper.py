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

# 🥇 DIZIONARIO POTENZIATO: Nome Comitato -> (Slug URL, Sigla DNA Attesa)
COMITATI_FISI = {
    'Trentino (TN)': ('trentino', 'TN'),
    'Alto Adige (AA)': ('alto-adige', 'AA'),           
    'Veneto (VE)': ('veneto', 'VE'),
    'Alpi Centrali (AC)': ('alpi-centrali', 'AC'),     
    'Alpi Occidentali (AOC)': ('alpi-occidentali', 'AOC'), 
    'Valdostano (ASIVA)': ('asiva', 'VA'), # In FISI la Valle d'Aosta usa spesso VA
    'Friuli Venezia Giulia (FVG)': ('friuli-venezia-giulia', 'FVG'), 
    'Appennino Emiliano (CAE)': ('appennino-emiliano', 'CAE'), 
    'Appennino Toscano (CAT)': ('appennino-toscano', 'CAT'),   
    'Abruzzo (CAB)': ('abruzzo', 'CAB'),
    'Lazio e Sardegna (CLS)': ('lazio-sardegna', 'CLS'),
    'Ligure (LIG)': ('ligure', 'LIG'),
    'Umbro Marchigiano (CUM)': ('umbro-marchigiano', 'CUM'),
    'Campano (CAM)': ('campano', 'CAM'),
    'Calabro Lucano (CAL)': ('calabro-lucano', 'CAL'),
    'Pugliese (PUG)': ('pugliese', 'PUG'),
    'Siculo (SIC)': ('siculo', 'SIC'),
}

# Tutte le sigle d'Italia per fare il controllo incrociato
TUTTE_LE_SIGLE = ['AA', 'AC', 'AOC', 'VA', 'ASIVA', 'CAB', 'CAE', 'CAL', 'CAM', 'CAT', 'CLS', 'CUM', 'FVG', 'LIG', 'PUG', 'SIC', 'TN', 'VE']

def analizza_dna_gara(item):
    """Estrae la sigla della gara dai dati nascosti per capire a chi appartiene davvero"""
    c = str(item.get("codiceComitato", "")).strip().upper()
    if not c: c = str(item.get("comitato", "")).strip().upper()
    
    if c in TUTTE_LE_SIGLE: return 'VA' if c == 'ASIVA' else c

    soc = str(item.get("codiceSocieta", "")).strip().upper()
    # Controlliamo le prime lettere del codice società (es. VE0036 -> VE)
    for sigla in sorted(TUTTE_LE_SIGLE, key=len, reverse=True):
        if soc.startswith(sigla):
            return 'VA' if sigla == 'ASIVA' else sigla
            
    return "SCONOSCIUTO"

# =====================================================================
# 🗓️ FASE 1: ASSEGNAZIONE A PRIORI + FILTRO ANTI-FURTO
# =====================================================================
def spider_calendari_nazionale():
    print("--- 🚀 FASE 1: DOWNLOAD A PRIORI CON PROTEZIONE ANTI-FURTO ---", flush=True)
    
    anno_corrente = datetime.datetime.now().year
    mese_corrente = datetime.datetime.now().month
    anno_massimo = anno_corrente + 1 if mese_corrente >= 6 else anno_corrente
    stagioni_da_scaricare = list(range(2020, anno_massimo + 1))
    
    LISTA_NERA = ["ALPINO", "SLALOM", "GIGANTE", "GS", "SUPER G", "DISCESA", "BIATHLON", "SNOWBOARD", "SKICROSS", "FREESTYLE", "ERBA", "SKELETON", "BOB", "JUMP", "SALTO"]
    
    gare_viste_globali = set()
    totale_salvate = 0
    
    for nome_comitato, dati in COMITATI_FISI.items():
        slug_sito = dati[0]
        sigla_attesa = dati[1]
        print(f"\n🌍 Bussiamo alla porta di: {nome_comitato}", flush=True)
        all_gare_fondo = []
        furti_sventati = 0
        
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
                        if id_comp in gare_viste_globali: continue
                            
                        disciplina = str(item.get("disciplina", "")).upper()
                        nome_gara = str(item.get("nome", "")).upper()
                        
                        is_fondo = any(k in disciplina for k in ["FONDO", "LANGLAUF", "NORDICO", "XC"]) or \
                                   any(k in nome_gara for k in ["FONDO", "LANGLAUF", "NORDICO", "CROSS COUNTRY", "XC"])
                        is_proibita = any(k in nome_gara for k in LISTA_NERA) or any(k in disciplina for k in LISTA_NERA)
                        
                        if is_fondo and not is_proibita:
                            
                            # 🛑 INTERVENTO DEL BUTTAFUORI:
                            dna_gara = analizza_dna_gara(item)
                            
                            # Se la gara ha un DNA palese di un ALTRA regione, la blocchiamo e non la salviamo!
                            if dna_gara != "SCONOSCIUTO" and dna_gara != sigla_attesa:
                                furti_sventati += 1
                                continue # Ignoriamo la gara, la pescheremo quando sarà il turno della sua vera regione
                                
                            gare_viste_globali.add(id_comp)
                            
                            # Eccezione per le gare mondiali
                            comitato_assegnato = nome_comitato
                            livello = str(item.get("livello", "")).upper()
                            if "WORLD" in livello or "OPA" in livello or "INTERNAZIONAL" in livello:
                                comitato_assegnato = "Internazionale/FIS"

                            record = {
                                "id_gara_fisi": id_comp, 
                                "gara_nome": item.get("nome", "Gara Senza Nome"),
                                "luogo": item.get("comune", "N/D"), 
                                "data_gara": item.get("dataInizio", "N/D"), 
                                "comitato": comitato_assegnato 
                            }
                            all_gare_fondo.append(record)
                            
                    if len(data) < limit: break
                    offset += limit
                    
                except Exception:
                    break 
            
            time.sleep(0.1)
            
        if all_gare_fondo:
            supabase.table("Gare").upsert(all_gare_fondo).execute()
            totale_salvate += len(all_gare_fondo)
            print(f"   ✅ Salvate {len(all_gare_fondo)} gare legittime per {nome_comitato}.", flush=True)
            if furti_sventati > 0:
                print(f"   🛡️ Il Buttafuori ha sventato {furti_sventati} furti di altre regioni!", flush=True)
        else:
            print(f"   ⏩ Nessuna gara NUOVA trovata.", flush=True)

    print(f"\n🏆 FASE 1 COMPLETATA! Totale Assoluto Gare Italia: {totale_salvate}", flush=True)

if __name__ == "__main__":
    spider_calendari_nazionale()
    # spider_atleti_master() <-- Disattivata per il test
