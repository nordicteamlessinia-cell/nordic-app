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
    print("Assicurati di aver impostato SUPABASE_URL e SUPABASE_KEY.")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# 🛠️ 2. FUNZIONI DI SUPPORTO
# ==========================================
def formatta_data_fis(testo_data):
    """Converte date della FIS nel formato YYYY-MM-DD per il database"""
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
# 🔍 3. MOTORE DI RICERCA GARE
# ==========================================
def recupera_ultime_gare(limite_gare=15):
    """Scansiona il codice sorgente del calendario FIS per trovare gli ID delle gare"""
    print(f"🌍 Cerco le ultime {limite_gare} gare completate sul calendario FIS...")
    
    url_calendario = "https://www.fis-ski.com/DB/cross-country/calendar-results.html?eventselection=actualresults&sectorcode=CC&racedatetype=onp&include_at_least_one_results=true"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    response = requests.get(url_calendario, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Errore nel caricamento del calendario: HTTP {response.status_code}")
        return []

    # Cerchiamo brutalmente qualsiasi numero associato a "raceid=" nel codice sorgente
    race_ids_trovati = re.findall(r'raceid=(\d+)', response.text, re.IGNORECASE)
    
    # Rimuoviamo i duplicati mantenendo l'ordine originale (le più recenti prima)
    race_ids_unici = list(dict.fromkeys(race_ids_trovati))
    
    # Tagliamo la lista al limite richiesto
    race_ids_finali = race_ids_unici[:limite_gare]
    
    print(f"🎯 Trovati {len(race_ids_finali)} ID gara univoci: {race_ids_finali}\n")
    return race_ids_finali

# ==========================================
# ⛷️ 4. ESTRATTORE RISULTATI E SALVATAGGIO
# ==========================================
def estrai_e_salva_gara(raceid):
    """Scarica i dati statici di una gara ed esegue l'upsert su Supabase"""
    url = f"https://www.fis-ski.com/DB/general/results.html?sectorcode=CC&raceid={raceid}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    print(f"🚀 Elaborazione gara {raceid}...")
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"   ❌ Errore API: HTTP {response.status_code}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # --- Estrazione Intestazione Gara ---
    try:
        luogo = soup.select_one(".event-header__name h1").text.strip() if soup.select_one(".event-header__name h1") else "N/D"
        data_gara = formatta_data_fis(soup.select_one(".date__full").text.strip() if soup.select_one(".date__full") else "N/D")
        categoria = soup.select_one(".event-header__kind").text.strip() if soup.select_one(".event-header__kind") else "FIS"
        specialita = soup.select_one(".event-header__subtitle").text.strip() if soup.select_one(".event-header__subtitle") else "Cross-Country"
    except Exception:
        luogo, data_gara, categoria, specialita = "N/D", datetime.datetime.now().strftime("%Y-%m-%d"), "FIS", "Cross-Country"

    # --- Estrazione Atleti ---
    righe_atleti = soup.find_all("a", class_="table-row")
    if not righe_atleti:
        print("   ⚠️ Nessun atleta trovato per questa gara.")
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

    # --- Salvataggio su Supabase ---
    if risultati_da_salvare:
        try:
            supabase.table("Risultati_Fis").upsert(risultati_da_salvare).execute()
            print(f"   ✅ Salvati {len(risultati_da_salvare)} atleti: {luogo} | {specialita} | {data_gara}")
        except Exception as e:
            print(f"   ❌ Errore Supabase durante il salvataggio: {e}")

# ==========================================
# 🚀 5. AVVIO DELLO SCRIPT
# ==========================================
if __name__ == "__main__":
    print("=========================================")
    print("❄️ AVVIO FIS SCRAPER BOT (CROSS-COUNTRY) ❄️")
    print("=========================================\n")
    
    # Definisci quante delle ultime gare vuoi analizzare ad ogni avvio (es. 15)
    gare_da_aggiornare = recupera_ultime_gare(limite_gare=15)
    
    if not gare_da_aggiornare:
        print("Nessuna gara trovata da processare. Termino lo script.")
        exit(0)

    for id_gara in gare_da_aggiornare:
        estrai_e_salva_gara(id_gara)
        # Pausa di rispetto di 1 secondo per non bombardare i server FIS
        time.sleep(1)
        
    print("\n🏁 Aggiornamento completato con successo!")
