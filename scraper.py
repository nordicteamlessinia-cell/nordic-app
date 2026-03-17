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
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'})

# 🗺️ MAPPATURA INVERSA PER GLI URL
COMITATI_FISI_REVERSE = {
    'Trentino (TN)': 'trentino', 'Alto Adige (AA)': 'alto-adige', 'Veneto (VE)': 'veneto',
    'Alpi Centrali (AC)': 'alpi-centrali', 'Alpi Occidentali (AOC)': 'alpi-occidentali',
    'Friuli Venezia Giulia (FVG)': 'friuli-venezia-giulia', 'Appennino Emiliano (CAE)': 'appennino-emiliano',
    'Appennino Toscano (CAT)': 'appennino-toscano', 'Abruzzo (CAB)': 'abruzzo',
    'Lazio e Sardegna (CLS)': 'lazio-sardegna', 'Umbro Marchigiano (CUM)': 'umbro-marchigiano',
    'Campano (CAM)': 'campano', 'Calabro Lucano (CAL)': 'calabro-lucano',
    'Pugliese (PUG)': 'pugliese', 'Siculo (SIC)': 'siculo', 'Ligure (LIG)': 'ligure',
    'Valdostano (ASIVA)': 'asiva'
}

# 🎯 LO SCANNER DEGLI ACRONIMI (Per non "rapire" gli atleti)
ACRONIMI_FISI = [
    "AA", "AC", "AOC", "CAB", "CAE", "CAL", "CAM", "CAT", "CLS", "CUM",
    "FVG", "LIG", "PUG", "SIC", "TN", "VA", "ASIVA", "VE",
    "GM1", "GM2", "GM3", "GM4", "GM5", "FFOO", "FFGG", "CSCA", "CS", "CC", "AM"
]

def calcola_stagione_fisi(data_gara):
    """Calcola la 'stagione' FISI corretta in base alla data della gara"""
    try:
        if not data_gara or data_gara == "N/D": return str(datetime.datetime.now().year)
        p = data_gara.split("/")
        if len(p) == 3:
            return str(int(p[2]) + 1) if int(p[1]) >= 6 else str(p[2])
    except: pass
    return str(datetime.datetime.now().year)

# =====================================================================
# ⛷️ FASE 2: ESTRAZIONE ATLETI E RISULTATI
# =====================================================================
def spider_atleti_master():
    print("\n--- 📂 FASE 2: RECUPERO GARE DAL DATABASE E DOWNLOAD ATLETI ---", flush=True)
    
    # 1. Peschiamo tutte le gare perfette che hai salvato in Fase 1
    response = supabase.table("Gare").select("id_gara_fisi, data_gara, gara_nome, luogo, comitato").execute()
    lista_gare = response.data

    if not lista_gare:
        print("❌ Nessuna gara trovata nel DB. Devi eseguire prima la Fase 1!")
        return

    print(f"--- ⏱️ INIZIO ESTRAZIONE SU {len(lista_gare)} GARE FONDO ---", flush=True)

    for gara in lista_gare:
        id_comp = gara.get('id_gara_fisi')
        data_g = gara.get('data_gara')
        nome_g = gara.get('gara_nome')
        luogo_g = gara.get('luogo')
        nome_comitato_gara = gara.get('comitato') 
        
        if not id_comp or not nome_comitato_gara: continue
        
        # CONTROLLO: La classifica di questa gara è già in Supabase?
        controllo_db = supabase.table("Risultati").select("id_comp_collegata").eq("id_comp_collegata", id_comp).limit(1).execute()
        if len(controllo_db.data) > 0:
            # print(f"   ⏩ Già scaricata, salto: {nome_g}", flush=True)
            continue

        # Troviamo la porta giusta per interrogare il sito (usiamo trentino come passpartout per internazionali e ignoti)
        slug_sito = COMITATI_FISI_REVERSE.get(nome_comitato_gara, 'trentino')
        stagione_fisi = calcola_stagione_fisi(data_g)
        
        print(f"\n🟢 Analizzo: {nome_g} ({luogo_g} - {data_g})", flush=True)
        url_comp = f"https://comitati.fisi.org/{slug_sito}/competizione/?idComp={id_comp}&d={stagione_fisi}"
        
        try:
            res = session.get(url_comp, timeout=20)
            soup = BeautifulSoup(res.text, 'html.parser')
            links = soup.find_all('a', href=True)
            # Estraiamo le sotto-gare ("idGara") per questa competizione
            id_sottogare = list(set([l['href'].split('idGara=')[1].split('&')[0] for l in links if 'idGara=' in l['href']]))
            
            if not id_sottogare:
                print("   ⏩ Classifica non ancora pubblicata per questo evento.", flush=True)
                continue

            # Per ogni sotto-gara, raschiamo i risultati!
            for id_g in id_sottogare:
                url_gara = f"https://comitati.fisi.org/{slug_sito}/gara/?idGara={id_g}&idComp={id_comp}&d={stagione_fisi}"
                r_data = session.get(url_gara, timeout=20)
                gara_soup = BeautifulSoup(r_data.text, 'html.parser')
                
                # --- Estrazione Categoria e Specialità ---
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

                # --- Estrazione Righe Atleti ---
                elementi_atleti = gara_soup.find_all('span', class_='x-text-content-text-primary')
                testi_atleti = [e.get_text(strip=True) for e in elementi_atleti if len(e.get_text(strip=True)) > 0]
                
                batch_atleti = []
                i = 0
                while i < len(testi_atleti) - 7:
                    # Riconosciamo l'inizio di una riga atleta (es. Posizione "1", "2")
                    if testi_atleti[i].isdigit() and testi_atleti[i+1].isdigit() and len(testi_atleti[i+1]) >= 3:
                        
                        blocco_atleta = testi_atleti[i:i+8]
                        comitato_vero_atleta = "N/D"
                        
                        # 🎯 LO SCANNER: Cerca il comitato dell'atleta dentro la sua riga
                        for testo in blocco_atleta:
                            if testo.upper() in ACRONIMI_FISI:
                                comitato_vero_atleta = testo.upper()
                                break
                        
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
                            "comitato": comitato_vero_atleta # Assegna il VERO comitato!
                        })
                        i += 8
                    else:
                        i += 1
                
                # Salvataggio su Supabase
                if batch_atleti:
                    supabase.table("Risultati").upsert(batch_atleti).execute()
                    print(f"   ✅ Trovati {len(batch_atleti)} atleti per la cat: {categoria_finale}", flush=True)
                
                time.sleep(0.3) # Cortesia per il server

        except Exception as e:
            print(f"   ❌ Errore sulla classifica {id_comp}: {e}", flush=True)

if __name__ == "__main__":
    spider_atleti_master()
