import os
import requests
import time
import datetime
from bs4 import BeautifulSoup
from supabase import create_client

# 🟢 INIZIALIZZAZIONE SUPABASE
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'}
BASE_URL_AJAX = "https://comitati.fisi.org/wp-admin/admin-ajax.php"

# 🗺️ IL DIZIONARIO PERFETTO DELLA NOSTRA CRONOLOGIA
COMITATI_FISI = {
    'Abruzzo (CAB)': 'abruzzo/calendario',
    'Alto Adige (AA)': 'altoadige/calendario-gare',
    'Alpi Centrali (AC)': 'alpicentrali/calendario-gare',
    'Alpi Occidentali (AOC)': 'aoc/calendario',
    'Appennino Emiliano (CAE)': 'cae/calendario',
    'Appennino Toscano (CAT)': 'cat/calendario',
    'Calabro Lucano (CAL)': 'cal/calendario',
    'Campano (CAM)': 'campano/calendario',
    'Friuli Venezia Giulia (FVG)': 'fvg/calendario',
    'Lazio e Sardegna (CLS)': 'cls/calendario',
    'Ligure (LIG)': 'ligure/calendario',
    'Pugliese (PUG)': 'pugliese/calendario',
    'Siculo (SIC)': 'siculo/calendario',
    'Trentino (TN)': 'trentino/calendario-gare',
    'Umbro Marchigiano (CUM)': 'cum/calendario',
    'Valdostano (ASIVA)': 'asiva/calendario',
    'Veneto (VE)': 'veneto/calendario'
}

def calcola_stagione_fisi(data_gara):
    try:
        if not data_gara or data_gara == "N/D": return "2026"
        p = data_gara.split("/")
        if len(p) == 3:
            return str(int(p[2]) + 1) if int(p[1]) >= 6 else str(p[2])
    except: pass
    return "2026"

# =====================================================================
# 🗓️ FASE 1: SPIDER DEI CALENDARI (Trova l'ID Segreto e Scarica)
# =====================================================================
def spider_calendari_fondo_nazionale():
    print("\n--- 📅 FASE 1: DOWNLOAD CALENDARI STORICI (SOLO FONDO) ---")
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    anno_corrente = datetime.datetime.now().year
    mese_corrente = datetime.datetime.now().month
    anno_massimo = anno_corrente + 1 if mese_corrente >= 6 else anno_corrente
    stagioni_da_scaricare = list(range(2020, anno_massimo + 1))
    
    for nome_comitato, percorso_base in COMITATI_FISI.items():
        print(f"\n🌍 Analizzo: {nome_comitato}...")
        
        slug_sito = percorso_base.split('/')[0]
        url_calendario = f"https://comitati.fisi.org/{percorso_base}/"
        
        # 🕵️‍♂️ L'ALGORITMO HACKER: Troviamo l'ID numerico nascosto della disciplina "Fondo"
        id_disciplina_fondo = ""
        try:
            res_cal = session.get(url_calendario, timeout=15)
            soup_cal = BeautifulSoup(res_cal.text, 'html.parser')
            
            # Cerca nel menu a tendina delle discipline
            for opt in soup_cal.find_all('option'):
                testo = opt.text.upper()
                if "FONDO" in testo or "NORDICO" in testo:
                    val = opt.get('value')
                    if val and val.strip() != "" and val != "-1" and val.upper() != "TUTTE":
                        id_disciplina_fondo = val.strip()
                        break
                        
            # Se il menu a tendina non c'è, cerca nei link della pagina
            if not id_disciplina_fondo:
                for link in soup_cal.find_all('a', href=True):
                    testo = link.text.upper()
                    if "FONDO" in testo or "NORDICO" in testo:
                        import urllib.parse
                        parsed = urllib.parse.urlparse(link['href'])
                        qs = urllib.parse.parse_qs(parsed.query)
                        if 'd' in qs: id_disciplina_fondo = qs['d'][0]; break
                        if 'disciplina' in qs: id_disciplina_fondo = qs['disciplina'][0]; break
        except Exception:
            pass
            
        if id_disciplina_fondo:
            print(f"   🔑 Trovato ID Segreto Fondo per {slug_sito}: '{id_disciplina_fondo}'")
        else:
            print(f"   ⚠️ ID non trovato, scarico tutto e filtro manualmente...")

        all_gare_fondo = []
        
        for anno in stagioni_da_scaricare:
            params = {
                "action": "competizioni_get_all",
                "offset": 0,
                "limit": 100,
                "url": url_calendario, 
                "idStagione": str(anno), 
                "disciplina": id_disciplina_fondo, # 🎯 USIAMO IL CODICE MAGICO (Scarica SOLO fondo!)
                "dataInizio": "01/01/2010",
                "dataFine": "31/12/203
