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

# 🥇 ORDINE STRATEGICO: Chi prima arriva, meglio alloggia.
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
# 🗓️ FASE 1: ASSEGNAZIONE A PRIORI PER COMITATO (Logica Pura)
# =====================================================================
def spider_calendari_nazionale():
    print("--- 🚀 FASE 1: DOWNLOAD CON ASSEGNAZIONE A PRIORI Pura ---", flush=True)
    
    anno_corrente = datetime.datetime.now().year
    mese_corrente = datetime.datetime.now().month
    anno_massimo = anno_corrente + 1 if mese_corrente >= 6 else anno_corrente
    stagioni_da_scaricare = list(range(2020, anno_massimo + 1))
    
    LISTA_NERA = ["ALPINO", "SLALOM", "GIGANTE", "GS", "SUPER G", "DISCESA", "BIATHLON", "SNOWBOARD", "SKICROSS", "FREESTYLE", "ERBA", "SKELETON", "BOB", "JUMP", "SALTO"]
    
    gare_viste_globali = set()
    totale_salvate = 0
    
    for nome_comitato, slug_sito in COMITATI_FISI.items():
        print(f"\n🌍 Interrogo URL: https://comitati.fisi.org/{slug_sito}/calendario/", flush=True)
        all_gare_fondo = []
        
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
                        
                        # Anti-Furto: Se è già stata presa dal Nord, il Sud non la tocca
                        if id_comp in gare_viste_globali: 
                            continue
                            
                        disciplina = str(item.get("disciplina", "")).upper()
                        nome_gara = str(item.get("nome", "")).upper()
                        
                        is_fondo = any(k in disciplina for k in ["FONDO", "LANGLAUF", "NORDICO", "XC"]) or \
                                   any(k in nome_gara for k in ["FONDO", "LANGLAUF", "NORDICO", "CROSS COUNTRY", "XC"])
                        is_proibita = any(k in nome_gara for k in LISTA_NERA) or any(k in disciplina for k in LISTA_NERA)
                        
                        if is_fondo and not is_proibita:
                            gare_viste_globali.add(id_comp)
                            
                            # ✨ ASSEGNAZIONE CIECA AL 100%
                            record = {
                                "id_gara_fisi": id_comp, 
                                "gara_nome": item.get("nome", "Gara Senza Nome"),
                                "luogo": item.get("comune", "N/D"), 
                                "data_gara": item.get("dataInizio", "N/D"), 
                                "comitato": nome_comitato # Assegnato a prescindere dal livello!
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
            print(f"   ✅ Salvate {len(all_gare_fondo)} gare per {nome_comitato}.", flush=True)
        else:
            print(f"   ⏩ Nessuna gara NUOVA di fondo trovata per {nome_comitato}.", flush=True)

    print(f"\n🏆 FASE 1 COMPLETATA! Totale Assoluto Gare Italia: {totale_salvate}", flush=True)

if __name__ == "__main__":
    spider_calendari_nazionale()
    # spider_atleti_master() <-- Disattivata per il test veloce
