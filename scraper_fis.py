import os
import time
import requests
import datetime
import re
from bs4 import BeautifulSoup
from supabase import create_client

# 🟢 INIZIALIZZAZIONE SUPABASE
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERRORE CRITICO: Variabili di ambiente Supabase mancanti!")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- FUNZIONI DI UTILITA' ---

def formatta_data_fis(testo_data):
    """Converte date della FIS nel formato YYYY-MM-DD"""
    if not testo_data or testo_data == "N/D":
        return datetime.datetime.now().strftime("%Y-%m-%d")
    
    try:
        clean_date = testo_data.split('\n')[0].strip()
        for fmt in ("%B %d, %Y", "%d %b %Y", "%d.%m.%Y", "%Y-%m-%d"):
            try:
                return datetime.datetime.strptime(clean_date, fmt).strftime("%Y-%m-%d")
            except:
                continue
    except:
        pass
    return datetime.datetime.now().strftime("%Y-%m-%d")


def recupera_ultime_gare(limite_gare=15):
    """Va sul calendario FIS ed estrae gli ID delle ultime gare disputate"""
    print("🌍 Cerco le ultime gare completate sul calendario FIS...")
    
    # URL del calendario filtrato per Cross-Country e solo gare con risultati
    url_calendario = "https://www.fis-ski.com/DB/cross-country/calendar-results.html?eventselection=actualresults&sectorcode=CC&racedatetype=onp&include_at_least_one_results=true"
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    response = requests.get(url_calendario, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Errore nel caricamento del calendario: HTTP {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    link_gare = soup.find_all("a", href=True)
    
    race_ids = []
    
    # Cerchiamo tutti i link che contengono 'raceid='
    for link in link_gare:
        href = link['href']
        if "raceid=" in href:
            # Estraiamo solo il numero con una regex
            match = re.search(r'raceid=(\d+)', href)
            if match:
                raceid = match.group(1)
                if raceid not in race_ids:
                    race_ids.append(raceid)
                    
    # Prendiamo solo le prime N gare (per non far girare il bot per ore al primo avvio)
    race_ids = race_ids[:limite_gare]
    print(f"🎯 Trovate {len(race_ids)} gare recenti da processare: {race_ids}\n")
    return race_ids


def estrai_e_salva_gara(raceid):
    """Scarica i risultati di una singola gara e li salva su Supabase"""
    url = f"https://www.fis-ski.com/DB/general/results.html?sectorcode=CC&raceid={raceid}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    print(f"🚀 Elaborazione gara {raceid}...")
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"   ❌ Errore HTTP {response.status_code}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # 1. Info Generali
    try:
        luogo = soup.select_one(".event-header__name h1").text.strip() if soup.select_one(".event-header__name h1") else "N/D"
        data_gara = formatta_data_fis(soup.select_one(".date__full").text.strip() if soup.select_one(".date__full") else "N/D")
        categoria = soup.select_one(".event-header__kind").text.strip() if soup.select_one(".event-header__kind") else "FIS"
        specialita = soup.select_one(".event-header__subtitle").text.strip() if soup.select_one(".event-header__subtitle") else "Cross-Country"
    except Exception:
        luogo, data_gara, categoria, specialita = "N/D", datetime.datetime.now().strftime("%Y-%m-%d"), "FIS", "Cross-Country"

    # 2. Atleti
    righe_atleti = soup.find_all("a", class_="table-row")
    if not righe_atleti:
        print("   ⚠️ Nessun atleta trovato.")
        return

    risultati_da_salvare = []

    for riga in righe_atleti:
        try:
            nome_tag = riga.find("div", class_="athlete-name")
            nome = nome_tag.text.strip() if nome_tag else "N/D"
            nazione = riga.find("span", class_="country__name-short").text.strip() if riga.find("span", class_="country__name-short") else "N/D"
            
            colonne = [col.text.strip() for col in riga.find_all("div") if col.text.strip()]
            
            posizione = colonne[0] if len(colonne) > 0 else "N/D"
            codice_fis = colonne[1] if len(colonne) > 1 else "N/D" 
            tempo = colonne[-2] if len(colonne) > 2 else "N/D"
            punti = colonne[-1] if len(colonne) > 2 else "0.00"
            
            record = {
                "id_gara_fis": str(raceid),
                "luogo": luogo,
                "data_gara": data_gara,
                "categoria": categoria,
                "specialita": specialita,
                "posizione": posizione,
                "codice_fis": codice_fis,
                "atleta_nome": nome,
                "nazione": nazione,
                "tempo": tempo,
                "punti_fis": punti,
                "comitato": "FIS"
            }
            risultati_da_salvare.append(record)
        except Exception:
            continue

    # 3. Salvataggio
    if risultati_da_salvare:
        try:
            supabase.table("Risultati_Fis").upsert(risultati_da_salvare).execute()
            print(f"   ✅ Salvati {len(risultati_da_salvare)} atleti per {luogo} ({specialita})")
        except Exception as e:
            print(f"   ❌ Errore Supabase: {e}")

# --- ESECUZIONE PRINCIPALE ---
if __name__ == "__main__":
    print("=========================================")
    print("❄️ AVVIO FIS SCRAPER BOT (CROSS-COUNTRY) ❄️")
    print("=========================================\n")
    
    # 1. Trova le gare (ho impostato il limite a 15, ma puoi cambiarlo a 50 se vuoi scaricare più storico)
    gare_da_aggiornare = recupera_ultime_gare(limite_gare=15)
    
    # 2. Processa ogni gara
    for id_gara in gare_da_aggiornare:
        estrai_e_salva_gara(id_gara)
        # Una pausa minuscola per non sovraccaricare i server FIS
        time.sleep(1)
        
    print("\n🏁 Aggiornamento completato con successo!")
