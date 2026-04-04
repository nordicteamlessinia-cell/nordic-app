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

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERRORE CRITICO: Variabili di ambiente Supabase mancanti!")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 🛡️ ARMATURA DI RETE (La stessa infallibile del bot italiano!)
session = requests.Session()
retries = Retry(total=5, backoff_factor=2, status_forcelist=[ 429, 500, 502, 503, 504 ])
session.mount('https://', HTTPAdapter(max_retries=retries))
session.mount('http://', HTTPAdapter(max_retries=retries))
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5'
})

def estrai_dati_gara(url_gara):
    """Entra nella pagina della gara ed estrae la classifica usando BeautifulSoup"""
    print(f"   🔍 Analizzo classifica: {url_gara}")
    try:
        res = session.get(url_gara, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')
    except Exception as e:
        print(f"   ⚠️ Errore connessione alla gara: {e}")
        return []

    risultati_da_salvare = []
    
    try:
        # Estrazione Dati Generali Gara (Testata)
        id_gara = url_gara.split("raceid=")[-1].split("&")[0]
        
        # Luogo
        h1_elem = soup.find(class_='event-header__name')
        luogo = h1_elem.find('h1').get_text(strip=True) if h1_elem and h1_elem.find('h1') else "N/D"
        
        # Data
        date_elem = soup.find(class_='date__full')
        data_gara_raw = date_elem.get_text(strip=True) if date_elem else datetime.datetime.now().strftime("%d/%m/%Y")
        
        # Categoria
        cat_elem = soup.find(class_='event-header__kind')
        categoria = cat_elem.get_text(strip=True) if cat_elem else "FIS"
        
        # Specialità
        spec_elem = soup.find(class_='event-header__subtitle')
        specialita = spec_elem.get_text(strip=True) if spec_elem else "Cross-Country"

        # Troviamo tutte le righe degli atleti
        righe_atleti = soup.find_all('a', class_='table-row')
        print(f"   ⛷️ Analizzo {len(righe_atleti)} righe trovate...")

        for i, riga in enumerate(righe_atleti):
            
            # 1. Cerchiamo il Codice FIS
            cod_elem = riga.find(class_='g-md-1')
            codice_fis = cod_elem.get_text(strip=True) if cod_elem else ""
            
            # 🛡️ IL BUTTAFUORI: Se non c'è un codice FIS numerico, NON è un atleta!
            if not codice_fis.isdigit() or len(codice_fis) < 5:
                continue 

            # 2. Posizione
            pos_elem = riga.find(class_='pr-1')
            posizione = pos_elem.get_text(strip=True) if pos_elem else str(i+1)
            
            # 3. Nome
            nome_elem = riga.find(class_='g-lg-4') or riga.find(class_='g-md-4')
            atleta_nome = nome_elem.get_text(strip=True).replace("\n", " ") if nome_elem else "Sconosciuto"
            
            # 4. Nazione
            naz_elem = riga.find(class_='country__name-short')
            nazione = naz_elem.get_text(strip=True) if naz_elem else "N/D"
            
            # 5. Tempo
            tempo_elem = riga.find(class_='justify-content-end pr-1') or riga.find(class_='justify-content-end')
            tempo = tempo_elem.get_text(strip=True) if tempo_elem else "N/D"
            
            # 6. Punti
            punti_elem = riga.find(class_='pl-1 g-sm-1') or riga.find(class_='pl-1')
            punti_fis = punti_elem.get_text(strip=True) if punti_elem else "0.00"

            record = {
                "id_gara_fis": id_gara,
                "data_gara": data_gara_raw,
                "luogo": luogo,
                "posizione": posizione,
                "codice_fis": codice_fis,
                "atleta_nome": atleta_nome,
                "nazione": nazione,
                "tempo": tempo,
                "punti_fis": punti_fis,
                "categoria": categoria,
                "specialita": specialita,
                "nome_comitato": "Internazionale",
                "comitato": "Internazionale"
            }
            risultati_da_salvare.append(record)
            
    except Exception as e:
        print(f"   ⚠️ Errore nell'estrazione: {e}")

    return risultati_da_salvare


def avvia_scraper_fis():
    print("--- 🚀 AVVIO BOT SCRAPER FIS (MODALITA' INVISIBILE) ---", flush=True)
    
    # 🎯 Includiamo i mesi della stagione agonistica
    mesi_da_cercare = ["11-2025", "12-2025", "01-2026", "02-2026", "03-2026"]
    totale_salvati = 0

    for mese in mesi_da_cercare:
        print(f"\n🌍 Mi collego al calendario FIS (Mese: {mese})...")
        url_mese = f"https://www.fis-ski.com/DB/cross-country/calendar-results.html?sectorcode=CC&seasoncode=2026&seasonmonth={mese}"
        
        try:
            res = session.get(url_mese, timeout=30)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Peschiamo tutti i link dal codice sorgente
            links = soup.find_all('a', href=True)
            url_gare_trovate = set()
            
            for l in links:
                href = l['href']
                # Controlliamo che sia il link di una gara vera
                if 'raceid=' in href and 'sectorcode=CC' in href:
                    url_completo = href if href.startswith("http") else f"https://www.fis-ski.com{href}"
                    url_gare_trovate.add(url_completo)
            
            print(f"🎯 Trovate {len(url_gare_trovate)} gare nel mese {mese}.")

            # Entriamo in ogni gara a estrarre i cioccolatini
            for url in url_gare_trovate:
                risultati = estrai_dati_gara(url)
                if risultati:
                    try:
                        supabase.table("Risultati_Fis").upsert(risultati).execute()
                        totale_salvati += len(risultati)
                        print(f"   ✅ Salvati {len(risultati)} atleti.")
                    except Exception as e:
                        print(f"   ❌ Errore Supabase: {e}")
                
                time.sleep(1) # Pausa di cortesia per non bombardare i server

        except Exception as e:
            print(f"⚠️ Errore col caricamento del mese {mese}: {e}")

    print(f"\n🏆 SCRAPING COMPLETATO! Totale atleti aggiornati: {totale_salvati}", flush=True)

if __name__ == "__main__":
    avvia_scraper_fis()
