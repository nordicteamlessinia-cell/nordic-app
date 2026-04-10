import os
import time
import requests
import datetime
import re
from bs4 import BeautifulSoup
from supabase import create_client

# ==========================================
# 🟢 1. CONFIGURAZIONI PRINCIPALI
# ==========================================
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# 🎛️ INTERRUTTORE MAGICO: 
# True = Salva solo atleti ITA (da gare di tutto il mondo)
# False = Salva tutti gli atleti di tutto il mondo
SALVA_SOLO_ITALIANI = False 

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
# 🗺️ 3. RICOGNITORE MENSILE (Bypassa l'impaginazione)
# ==========================================
def recupera_tutti_gli_eventi():
    """Scansiona il calendario MESE per MESE per non farsi tagliare fuori dall'impaginazione"""
    print(f"🌍 Fase 1: Scansione completa del calendario Mondiale 2026 (Mese per Mese)...")
    
    # Mesi tipici della stagione invernale FIS
    mesi_stagione = ["10-2025", "11-2025", "12-2025", "01-2026", "02-2026", "03-2026", "04-2026"]
    tutti_gli_eventi = []
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    for mese in mesi_stagione:
        print(f"   📅 Esploro il mese: {mese}...")
        url_calendario = (
            f"https://www.fis-ski.com/DB/cross-country/calendar-results.html"
            f"?eventselection=&place=&sectorcode=CC&seasoncode=2026&categorycode="
            f"&disciplinecode=&gendercode=&racedate=&racecodex=&nationcode="
            f"&seasonmonth={mese}&saveselection=-1&seasonselection="
            f"&include_at_least_one_results=true"
        )
        
        try:
            response = requests.get(url_calendario, headers=headers, timeout=30)
            if response.status_code == 200:
                # Troviamo gli eventi di questo mese
                event_ids = re.findall(r'eventid=(\d+)', response.text, re.IGNORECASE)
                for eid in event_ids:
                    if eid not in tutti_gli_eventi:
                        tutti_gli_eventi.append(eid)
            time.sleep(0.5) # Pausa gentile tra un mese e l'altro
        except Exception as e:
            print(f"   ❌ Errore nel mese {mese}: {e}")
            
    print(f"🎯 Finito! Trovati in totale {len(tutti_gli_eventi)} Eventi unici per la stagione.\n")
    return tutti_gli_eventi

def recupera_gare_da_evento(eventid):
    """Apre la pagina dell'evento e trova tutte le singole GARE (raceid) al suo interno"""
    url_evento = f"https://www.fis-ski.com/DB/general/event-details.html?sectorcode=CC&eventid={eventid}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        response = requests.get(url_evento, headers=headers, timeout=30)
        if response.status_code != 200:
            return []
            
        race_ids = re.findall(r'raceid=(\d+)', response.text, re.IGNORECASE)
        # Rimuove i duplicati mantenendo l'ordine
        return list(dict.fromkeys(race_ids))
    except Exception:
        return []

# ==========================================
# ⚡ 4. ESTRATTORE VELOCE RISULTATI
# ==========================================
def estrai_e_salva_gara(raceid):
    """Estrae i risultati della gara e li salva su Supabase filtrando per nazione se richiesto"""
    url = f"https://www.fis-ski.com/DB/general/results.html?sectorcode=CC&raceid={raceid}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            return
    except Exception:
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Intestazione
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
            
            # 🛡️ FILTRO NAZIONALITA'
            if SALVA_SOLO_ITALIANI and nazione != "ITA":
                continue
            
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
    
    # 1. Trova TUTTI gli eventi della stagione divisa per mesi
    eventi_da_analizzare = recupera_tutti_gli_eventi()
    
    if not eventi_da_analizzare:
        print("Nessun evento trovato da processare. Termino lo script.")
        exit(0)

    # 2. Per ogni evento, trova le gare e scaricale
    for id_evento in eventi_da_analizzare:
        print(f"\n🎿 Esploro l'evento {id_evento}...")
        gare_dell_evento = recupera_gare_da_evento(id_evento)
        
        if gare_dell_evento:
            print(f"   Trovate {len(gare_dell_evento)} gare. Inizio download...")
            for id_gara in gare_dell_evento:
                estrai_e_salva_gara(id_gara)
                time.sleep(0.3) # Piccola pausa per non stressare la FIS
        else:
            print("   Nessuna gara con risultati trovata in questo evento.")
            
        time.sleep(0.5) 
        
    print("\n🏆 Aggiornamento completato con successo! Tutti i dati sono su Supabase.")
