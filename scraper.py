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

# 🗺️ DIZIONARIO OTTIMIZZATO PER SCI DI FONDO (Parametro &dis=F o &d=F)
COMITATI_FISI = {
    'Abruzzo (CAB)': 'abruzzo/calendario/?dis=F',
    'Alto Adige (AA)': 'altoadige/calendario-gare/?dis=F',
    'Alpi Centrali (AC)': 'alpicentrali/calendario-gare/?dis=F',
    'Alpi Occidentali (AOC)': 'aoc/calendario/?dis=F',
    'Appennino Emiliano (CAE)': 'cae/calendario/?dis=F',
    'Appennino Toscano (CAT)': 'cat/calendario/?dis=F',
    'Friuli Venezia Giulia (FVG)': 'fvg/calendario/?dis=F',
    'Trentino (TN)': 'trentino/calendario-gare/?dis=F',
    'Valdostano (ASIVA)': 'asiva/calendario/?dis=F',
    'Veneto (VE)': 'veneto/calendario/?dis=F'
}

def spider_calendari_fondo_nazionale():
    print("\n--- 🏁 ESTRAZIONE CALENDARI NAZIONALI - SOLO SCI DI FONDO ---")
    
    for nome_comitato, percorso in COMITATI_FISI.items():
        print(f"\n🌍 Cerco fondo per: {nome_comitato}...")
        
        # URL con filtro disciplina Fondo
        url_calendario = f"https://comitati.fisi.org/{percorso}"
        
        try:
            res = requests.get(url_calendario, headers=HEADERS, timeout=15)
            
            # Gestione automatica dei 404 (alcuni siti cambiano tra calendario e calendario-gare)
            if res.status_code == 404:
                percorso_alt = percorso.replace("calendario-gare", "calendario") if "calendario-gare" in percorso else percorso.replace("calendario", "calendario-gare")
                url_calendario = f"https://comitati.fisi.org/{percorso_alt}"
                res = requests.get(url_calendario, headers=HEADERS, timeout=15)

            if res.status_code != 200:
                print(f"   ❌ Errore {res.status_code} su {url_calendario}")
                continue
                
            soup = BeautifulSoup(res.text, 'html.parser')
            righe = soup.find_all('tr')
            batch_gare = []
            
            for riga in righe:
                colonne = riga.find_all('td')
                if len(colonne) < 3: continue
                
                # Cerchiamo il link della competizione
                link_tag = riga.find('a', href=True)
                if not link_tag or 'idComp=' not in link_tag['href']:
                    continue
                
                # FILTRO EXTRA: Verifichiamo se nella riga c'è scritto "FONDO" o "CC" (Cross Country)
                # Spesso la colonna disciplina è la quarta o quinta
                testo_riga = riga.get_text().upper()
                # Se la pagina è già filtrata via URL questo è un controllo di sicurezza in più
                
                try:
                    id_comp = link_tag['href'].split('idComp=')[1].split('&')[0]
                    data_g = colonne[0].get_text(strip=True)
                    luogo_g = colonne[1].get_text(strip=True)
                    nome_g = colonne[2].get_text(strip=True)
                    
                    batch_gare.append({
                        "id_gara_fisi": id_comp,
                        "data_gara": data_g,
                        "luogo": luogo_g,
                        "gara_nome": nome_g,
                        "comitato": nome_comitato,
                        "disciplina": "Sci di Fondo" # Specifichiamo nel DB
                    })
                except:
                    continue
            
            if batch_gare:
                supabase.table("Gare").upsert(batch_gare).execute()
                print(f"   ✅ Trovate e salvate {len(batch_gare)} gare di FONDO.")
            else:
                print(f"   ⏩ Nessuna gara di fondo trovata per questo comitato.")
            
            time.sleep(0.8)

        except Exception as e:
            print(f"   ❌ Errore: {e}")

if __name__ == "__main__":
    spider_calendari_fondo_nazionale()
