import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
from bs4 import BeautifulSoup
from supabase import create_client
import datetime

# 🟢 INIZIALIZZAZIONE SUPABASE
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 🛡️ ARMATURA DI RETE (Simuliamo un browser umano)
session = requests.Session()
retries = Retry(total=5, backoff_factor=2, status_forcelist=[ 429, 500, 502, 503, 504 ])
session.mount('https://', HTTPAdapter(max_retries=retries))
session.mount('http://', HTTPAdapter(max_retries=retries))

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7',
}
session.headers.update(HEADERS)

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
# 🗓️ FASE 1: HTML SCRAPER (Legge i link direttamente dalle pagine visibili)
# =====================================================================
def spider_calendari_html():
    print("--- 🚀 FASE 1: SCANSIONE FRONT-END (HTML) DEI CALENDARI ---", flush=True)
    
    anno_corrente = datetime.datetime.now().year
    mese_corrente = datetime.datetime.now().month
    anno_massimo = anno_corrente + 1 if mese_corrente >= 6 else anno_corrente
    stagioni_da_scaricare = list(range(2020, anno_massimo + 1))
    
    gare_viste_globali = set()
    
    for nome_comitato, slug_sito in COMITATI_FISI.items():
        print(f"\n🌍 Navigo sito HTML: {nome_comitato}...", flush=True)
        all_gare_comitato = []
        
        # Testiamo quale pagina HTML usa il comitato per mostrare le gare
        percorsi_da_testare = ["competizioni", "calendario", "gare", "calendario-gare", ""]
        url_base_comitato = None
        
        for percorso in percorsi_da_testare:
            test_url = f"https://comitati.fisi.org/{slug_sito}/{percorso}/" if percorso else f"https://comitati.fisi.org/{slug_sito}/"
            try:
                # Simuliamo la visita umana alla pagina
                res = session.get(test_url, timeout=15)
                # Se la pagina esiste (200) e contiene la parola idComp (che sono i link alle gare)
                if res.status_code == 200 and 'idComp=' in res.text:
                    url_base_comitato = test_url
                    print(f"   🔑 Pagina Web trovata: {url_base_comitato}", flush=True)
                    break
            except:
                pass

        if not url_base_comitato:
            print(f"   ⏩ Nessuna pagina calendario HTML valida trovata per questo comitato.", flush=True)
            continue

        for anno in stagioni_da_scaricare:
            # Aggiungiamo il parametro dell'anno come farebbe un utente che usa il menù a tendina
            url_anno = f"{url_base_comitato}?d={anno}"
            
            try:
                res = session.get(url_anno, timeout=20)
                soup = BeautifulSoup(res.text, 'html.parser')
                
                # Cerchiamo TUTTI i link <a> presenti nella pagina
                links = soup.find_all('a', href=True)
                
                contatore_anno = 0
                for link in links:
                    href = link['href']
                    
                    # Se il link porta a una competizione
                    if 'idComp=' in href:
                        try:
                            # Estraiamo il numero magico (l'ID della gara) direttamente dall'URL
                            id_comp = href.split('idComp=')[1].split('&')[0]
                            
                            if id_comp in gare_viste_globali:
                                continue
                                
                            nome_gara_html = link.get_text(strip=True).upper()
                            
                            # Filtro basilare visivo per assicurarci che sia sci di fondo
                            is_fondo = any(k in nome_gara_html for k in ["FONDO", "LANGLAUF", "TROFEO", "COPPA", "MEMORIAL", "CAMPIONATO", "REGIONALE", "XC"])
                            is_alpino = any(k in nome_gara_html for k in ["ALPINO", "SLALOM", "GIGANTE", "DISCESA", "SNOWBOARD", "BIATHLON"])
                            
                            # Se l'HTML della riga della tabella non contiene il nome, lo prenderemo in modo definitivo nella Fase 2
                            if not nome_gara_html:
                                nome_gara_html = "GARA IN FASE DI DOWNLOAD"
                            
                            if not is_alpino:
                                gare_viste_globali.add(id_comp)
                                
                                # IL PUNTO CRUCIALE: Assegniamo forzatamente il comitato della pagina che stiamo guardando!
                                record = {
                                    "id_gara_fisi": id_comp, 
                                    "gara_nome": nome_gara_html,
                                    "luogo": "Da scaricare", # Verrà aggiornato precisamente dalla Fase 2
                                    "data_gara": f"01/01/{anno}", # Data temporanea, verrà sovrascritta dalla Fase 2
                                    "comitato": nome_comitato 
                                }
                                all_gare_comitato.append(record)
                                contatore_anno += 1
                        except:
                            pass
                            
            except Exception as e:
                pass

        if all_gare_comitato:
            supabase.table("Gare").upsert(all_gare_comitato).execute()
            print(f"   ✅ Salvati {len(all_gare_comitato)} link unici di gare per il {nome_comitato}.", flush=True)
        else:
            print(f"   ⏩ Nessuna gara compatibile trovata nell'HTML.", flush=True)
        
        time.sleep(0.5)

if __name__ == "__main__":
    spider_calendari_html()
    # La Fase 2 scaricherà atleti, date esatte e luoghi esatti entrando in ogni singolo link trovato qui sopra.
    print("\n🏁 FASE 1 COMPLETATA! Controlla se le attribuzioni dei comitati ora sono perfette! 🏁", flush=True)
