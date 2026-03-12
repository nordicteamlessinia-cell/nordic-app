import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import datetime
from bs4 import BeautifulSoup
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

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'}
session.headers.update(HEADERS)

BASE_URL_AJAX = "https://comitati.fisi.org/wp-admin/admin-ajax.php"

COMITATI_FISI = {
    'Abruzzo (CAB)': 'abruzzo',
    'Alto Adige (AA)': 'alto-adige',           
    'Alpi Centrali (AC)': 'alpi-centrali',     
    'Alpi Occidentali (AOC)': 'alpi-occidentali', 
    'Appennino Emiliano (CAE)': 'appennino-emiliano', 
    'Appennino Toscano (CAT)': 'appennino-toscano',   
    'Calabro Lucano (CAL)': 'calabro-lucano',
    'Campano (CAM)': 'campano',
    'Friuli Venezia Giulia (FVG)': 'friuli-venezia-giulia', 
    'Lazio e Sardegna (CLS)': 'lazio-sardegna',
    'Ligure (LIG)': 'ligure',
    'Pugliese (PUG)': 'pugliese',
    'Siculo (SIC)': 'siculo',
    'Trentino (TN)': 'trentino',
    'Umbro Marchigiano (CUM)': 'umbro-marchigiano',
    'Valdostano (ASIVA)': 'asiva',
    'Veneto (VE)': 'veneto'
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
# 🗓️ FASE 1: DOWNLOAD CON CONTROLLO "DOPPIA MANDATA"
# =====================================================================
def spider_calendari_nazionale():
    print("--- 🚀 FASE 1: DOWNLOAD CALENDARI NAZIONALI (DAL 2020) ---")
    
    anno_corrente = datetime.datetime.now().year
    mese_corrente = datetime.datetime.now().month
    anno_massimo = anno_corrente + 1 if mese_corrente >= 6 else anno_corrente
    stagioni_da_scaricare = list(range(2020, anno_massimo + 1))
    
    # LA LISTA NERA: Qualsiasi gara contenga queste parole viene incenerita.
    LISTA_NERA = ["ALPINO", "SLALOM", "GIGANTE", "GS", "SUPER G", "DISCESA", "BIATHLON", "SNOWBOARD", "SKICROSS", "FREESTYLE", "ERBA", "SKELETON", "BOB", "JUMP", "SALTO"]
    
    for nome_comitato, slug_sito in COMITATI_FISI.items():
        print(f"\n🌍 Analizzo: {nome_comitato}...")
        all_gare_fondo = []
        
        for anno in stagioni_da_scaricare:
            params = {
                "action": "competizioni_get_all",
                "offset": 0,
                "limit": 100,
                "url": f"https://comitati.fisi.org/{slug_sito}/calendario/",
                "idStagione": str(anno),
                "disciplina": "", 
                "dataInizio": "01/01/2010",
                "dataFine": "31/12/2030"
            }
            
            try:
                while True:
                    r = session.get(BASE_URL_AJAX, params=params, timeout=30)
                    data = r.json()
                    if not data: break

                    for item in data:
                        disciplina_ufficiale = str(item.get("disciplina", "")).upper()
                        nome_gara = str(item.get("nome", "")).upper()
                        
                        # CONTROLLO 1: È Fondo secondo la FISI o secondo il nome?
                        is_fondo = ("FONDO" in disciplina_ufficiale or "LANGLAUF" in disciplina_ufficiale or "NORDICO" in disciplina_ufficiale) or ("FONDO" in nome_gara or "LANGLAUF" in nome_gara or "CROSS COUNTRY" in nome_gara)
                        
                        # CONTROLLO 2: Contiene parole proibite?
                        is_proibita = any(parola in nome_gara for parola in LISTA_NERA) or any(parola in disciplina_ufficiale for parola in LISTA_NERA)
                        
                        # VERDETTO FINALE
                        if is_fondo and not is_proibita:
                            record = {
                                "id_gara_fisi": str(item.get("idCompetizione")), 
                                "gara_nome": item.get("nome"),
                                "luogo": item.get("comune", "N/D"), 
                                "data_gara": item.get("dataInizio", "N/D"), 
                                "comitato": nome_comitato 
                            }
                            if record not in all_gare_fondo:
                                all_gare_fondo.append(record)
                        
                    params["offset"] += params["limit"]
                    
            except Exception as e:
                pass

        if all_gare_fondo:
            print(f"   💾 INVIO {len(all_gare_fondo)} GARE BLINDATE A SUPABASE")
            supabase.table("Gare").upsert(all_gare_fondo).execute()
        else:
            print(f"   ⏩ Nessuna gara di Fondo trovata.")
        
        time.sleep(0.5)

# =====================================================================
# ⛷️ FASE 2: ESTRAZIONE ATLETI E TEMPI
# =====================================================================
def spider_atleti_master():
    print("\n--- 📂 FASE 2: RECUPERO GARE DAL DATABASE E DOWNLOAD ATLETI ---")
    
    gare_db = supabase.table("Gare").select("id_gara_fisi, data_gara, gara_nome, luogo, comitato").execute()
    lista_gare = gare_db.data

    print(f"--- ⏱️ INIZIO ESTRAZIONE SU {len(lista_gare)} GARE FONDO ---")

    for gara in lista_gare:
        id_comp = gara.get('id_gara_fisi')
        data_g = gara.get('data_gara')
        nome_g = gara.get('gara_nome')
        luogo_g = gara.get('luogo')
        nome_comitato = gara.get('comitato')
        
        if not id_comp or not nome_comitato: continue
        
        slug_sito = COMITATI_FISI.get(nome_comitato)
        if not slug_sito: continue
        
        stagione_fisi = calcola_stagione_fisi(data_g)
        print(f"\n🟢 Scarico: {nome_g} ({luogo_g} - {data_g})")
        
        url_comp = f"https://comitati.fisi.org/{slug_sito}/competizione/?idComp={id_comp}&d={stagione_fisi}"
        
        try:
            res = session.get(url_comp, timeout=20)
            soup = BeautifulSoup(res.text, 'html.parser')
            links = soup.find_all('a', href=True)
            id_sottogare = list(set([l['href'].split('idGara=')[1].split('&')[0] for l in links if 'idGara=' in l['href']]))
            
            if not id_sottogare:
                print("   ⏩ Classifica non ancora pubblicata.")
                continue

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
                        batch_atleti.append({
                            "id_gara_fisi": id_g, 
                            "id_comp_collegata": id_comp, 
                            "posizione": int(testi_atleti[i]),
                            "atleta_nome": testi_atleti[i+2],
                            "societa": testi_atleti[i+4],
                            "tempo": testi_atleti[i+5], 
                            "categoria": categoria_finale,
                            "gara_nome": nome_g,
                            "luogo": luogo_g,
                            "data_gara": data_g,
                            "comitato": nome_comitato
                        })
                        i += 8
                    else:
                        i += 1
                
                if batch_atleti:
                    supabase.table("Risultati").upsert(batch_atleti).execute()
                    print(f"   ✅ Salvati {len(batch_atleti)} atleti/tempi!")
                
                time.sleep(0.3)

        except Exception as e:
            print(f"   ❌ Errore sull'evento {id_comp}: {e}")

if __name__ == "__main__":
    spider_calendari_nazionale()
    spider_atleti_master()
