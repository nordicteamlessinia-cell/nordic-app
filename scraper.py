import os
import requests
import time
from bs4 import BeautifulSoup
from supabase import create_client

# Configurazione Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'}

# 🗺️ DIZIONARIO NAZIONALE DEI COMITATI
# La chiave è il nome che scriveremo nel DB, il valore è la parte dell'URL del sito FISI
COMITATI_FISI = {
    'Abruzzo (CAB)': 'abruzzo',
    'Alto Adige (AA)': 'altoadige',
    'Alpi Centrali (AC)': 'alpicentrali',
    'Alpi Occidentali (AOC)': 'aoc',
    'Appennino Emiliano (CAE)': 'cae',
    'Appennino Toscano (CAT)': 'cat',
    'Calabro Lucano (CAL)': 'cal',
    'Campano (CAM)': 'campano',
    'Friuli Venezia Giulia (FVG)': 'fvg',
    'Lazio e Sardegna (CLS)': 'cls',
    'Ligure (LIG)': 'ligure',
    'Pugliese (PUG)': 'pugliese',
    'Siculo (SIC)': 'siculo',
    'Trentino (TN)': 'trentino',
    'Umbro Marchigiano (CUM)': 'cum',
    'Valdostano (ASIVA)': 'asiva',
    'Veneto (VE)': 'veneto'
}

def spider_calendari_tutta_italia():
    print("\n--- 🏁 INIZIO ESTRAZIONE CALENDARI NAZIONALI ---")
    
    gare_totali_salvate = 0

    for nome_comitato, slug_sito in COMITATI_FISI.items():
        print(f"\n🌍 Cerco gare per: {nome_comitato}...")
        
        # Costruiamo l'URL specifico per il comitato corrente
        url_calendario = f"https://comitati.fisi.org/{slug_sito}/calendario/"
        
        try:
            res = requests.get(url_calendario, headers=HEADERS, timeout=15)
            if res.status_code != 200:
                print(f"   ⚠️ Impossibile raggiungere il sito per {nome_comitato} (Errore {res.status_code})")
                continue
                
            soup = BeautifulSoup(res.text, 'html.parser')
            righe = soup.find_all('tr')
            batch_gare = []
            
            for riga in righe:
                colonne = riga.find_all('td')
                if len(colonne) < 5: 
                    continue
                
                link_tag = riga.find('a', href=True)
                if not link_tag or 'idComp=' not in link_tag['href']:
                    continue
                
                try:
                    # Estrazione dati
                    id_comp = link_tag['href'].split('idComp=')[1].split('&')[0]
                    data_g = colonne[0].get_text(strip=True)
                    luogo_g = colonne[1].get_text(strip=True)
                    nome_g = colonne[2].get_text(strip=True)
                    
                    # Preparazione riga per Supabase con colonna COMITATO
                    batch_gare.append({
                        "id_gara_fisi": id_comp,
                        "data_gara": data_g,
                        "luogo": luogo_g,
                        "gara_nome": nome_g,
                        "comitato": nome_comitato  # ✨ Specifica il comitato di appartenenza
                    })
                except Exception:
                    continue
            
            # Salvataggio nel database per questo comitato
            if batch_gare:
                supabase.table("Gare").upsert(batch_gare).execute()
                print(f"   ✅ Salvate {len(batch_gare)} gare per {nome_comitato}")
                gare_totali_salvate += len(batch_gare)
            else:
                print(f"   ⏩ Nessuna gara trovata per {nome_comitato}")
            
            # Piccola pausa per non sovraccaricare il server FISI
            time.sleep(0.5)

        except Exception as e:
            print(f"   ❌ Errore durante lo scraping di {nome_comitato}: {e}")

    print(f"\n--- 🏆 FINE! Gare totali elaborate: {gare_totali_salvate} ---")

if __name__ == "__main__":
    spider_calendari_tutta_italia()
