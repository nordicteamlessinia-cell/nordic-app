import os
import time
import requests
import datetime
import re
from bs4 import BeautifulSoup
from supabase import create_client

# ==========================================
# 🟢 1. CONFIGURAZIONE SUPABASE
# ==========================================
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERRORE CRITICO: Variabili di ambiente Supabase mancanti!")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# 🛠️ 2. FUNZIONI DI SUPPORTO
# ==========================================
def formatta_data_fis(testo_data):
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

# ==========================================
# 🗺️ 3. RICOGNITORE EVENTI E GARE
# ==========================================
def recupera_ultimi_eventi(limite_eventi=15):
    """Fase 1: Legge il calendario e trova gli ID degli Eventi (es. il weekend a Falcade)"""
    print(f"🌍 Fase 1: Cerco gli ultimi {limite_eventi} EVENTI sul calendario ITA 2026...")
    
    url_calendario = (
        "https://www.fis-ski.com/DB/cross-country/calendar-results.html"
        "?eventselection=&place=&sectorcode=CC&seasoncode=2026&categorycode="
        "&disciplinecode=&gendercode=&racedate=&racecodex=&nationcode=ita"
        "&seasonmonth=X-2026&saveselection=-1&seasonselection="
        "&include_at_least_one_results=true"
    )
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        response = requests.get(url_calendario, headers=headers, timeout=30)
        if response.status_code != 200:
            print(f"❌ Errore API Calendario: HTTP {response.status_code}")
            return []

        # Cerchiamo EVENTID invece di RACEID!
        event_ids_trovati = re.findall(r'eventid=(\d+)', response.text, re.IGNORECASE)
        event_ids_unici = list(dict.fromkeys(event_ids_trovati))[:limite_eventi]
        
        print(f"🎯 Trovati {len(event_ids_unici)} Eventi: {event_ids_unici}\n")
        return event_ids_unici
    except Exception as e:
        print(f"❌ Errore di connessione al calendario: {e}")
        return []

def recupera_gare_da_evento(eventid):
    """Fase 2: Apre la pagina dell'evento e trova tutte le singole GARE (raceid) al suo interno"""
    url_evento = f"https://www.fis-ski.com/DB/general/event-details.html?sectorcode=CC&eventid={eventid}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        response = requests.get(url_evento, headers=headers, timeout=30)
        if response.status_code != 200:
            return []
            
        race_ids = re.findall(r'raceid=(\d+)', response.text, re.IGNORECASE)
        return list(dict.fromkeys(race_ids))
    except Exception:
        return []

# ==========================================
# ⚡ 4. ESTRATTORE VELOCE RISULTATI
# ==========================================
def estrai_e_salva_gara(raceid):
    """Fase 3: Estrae i risultati della gara e li salva su Supabase"""
    url = f"https://www.fis-ski.com/DB/general/results.html?sectorcode=CC&raceid={raceid}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    print(f"   🚀 Scarico i dati della gara {raceid}...")
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            return
    except Exception:
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    
    try:
        luogo = soup.select_one(".event-header__name h1").text.strip() if soup.select_one(".event-header__name h1") else "N/D"
        data_gara = formatta_data_fis(soup.select_one(".date__full").text.strip() if soup.select_one(".date__full") else "N/D")
        categoria = soup.select_one(".event-header__kind").text.strip() if soup.select_one(".event-header__kind") else "FIS"
        specialita = soup.select_one(".event-header__subtitle").text.strip() if soup.select_one(".event-header__subtitle") else "Cross-Country"
    except Exception:
        luogo, data_gara, categoria, specialita = "N/D", datetime.datetime.now().strftime("%Y-%m-%d"), "FIS", "Cross-Country"

    righe_atleti = soup.find_all("a", class_="table-row")
    if not righe_atleti:
        return

    risultati_da_salvare = []

    for riga in righe_atleti:
        try:
            nome_tag = riga.find("div", class_="athlete-name")
            nome = nome_tag.text.strip() if nome_tag else "N/D"
            nazione_tag = riga.find("span", class_="country__name-short")
            nazione = nazione_tag.text.strip() if nazione_tag else "N/D"
            
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

    if risultati_da_salvare:
        try:
            supabase.table("Risultati_Fis").upsert(risultati_da_salvare).execute()
            print(f"      ✅ Salvati {len(risultati_da_salvare)} atleti: {luogo} | {specialita}")
        except Exception as e:
            print(f"      ❌ Errore Supabase: {e}")

# ==========================================
# 🏁 5. AVVIO DELLO SCRIPT
# ==========================================
if __name__ == "__main__":
    print("=========================================")
    print("❄️ AVVIO FIS SCRAPER BOT (CROSS-COUNTRY) ❄️")
    print("=========================================\n")
    
    # 1. Trova gli eventi
    eventi_da_analizzare = recupera_ultimi_eventi(limite_eventi=10)
    
    if not eventi_da_analizzare:
        print("Nessun evento trovato da processare. Termino lo script.")
        exit(0)

    # 2. Per ogni evento, trova le gare e scaricale
    for id_evento in eventi_da_analizzare:
        print(f"\n🎿 Esploro l'evento {id_evento}...")
        gare_dell_evento = recupera_gare_da_evento(id_evento)
        print(f"   Trovate {len(gare_dell_evento)} gare in questo evento: {gare_dell_evento}")
        
        for id_gara in gare_dell_evento:
            estrai_e_salva_gara(id_gara)
            time.sleep(0.5) # Pausa tra una gara e l'altra
            
        time.sleep(1) # Pausa tra un evento e l'altro
        
    print("\n🏆 Aggiornamento completato con successo! Tutti i dati sono su Supabase.")
