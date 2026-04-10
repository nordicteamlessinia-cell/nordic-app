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
    print("Assicurati di aver impostato SUPABASE_URL e SUPABASE_KEY su GitHub Actions.")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ==========================================
# 🛠️ 2. FUNZIONI DI SUPPORTO
# ==========================================
def formatta_data_fis(testo_data):
    """Converte date della FIS nel formato YYYY-MM-DD per Supabase"""
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
# 🗺️ 3. RICOGNITORE (Requests Puro) - Trova gli ID delle gare
# ==========================================
def recupera_ultime_gare(limite_gare=50):
    """Scarica il codice della pagina calendario ITA 2026 ed estrae i raceid"""
    print(f"🌍 Avvio il Ricognitore Veloce (Italia, Stagione 2026)...")
    
    # L'URL chirurgico con il filtro per l'Italia e per le gare concluse
    url_calendario = (
        "https://www.fis-ski.com/DB/cross-country/calendar-results.html"
        "?eventselection=&place=&sectorcode=CC&seasoncode=2026&categorycode="
        "&disciplinecode=&gendercode=&racedate=&racecodex=&nationcode=ita"
        "&seasonmonth=X-2026&saveselection=-1&seasonselection="
        "&include_at_least_one_results=true"
    )
    
    # Usiamo una Sessione per mantenere eventuali cookie e sembrare più umani
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    }
    
    try:
        print("⏳ Scarico i dati del calendario...")
        response = session.get(url_calendario, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Errore API Calendario: HTTP {response.status_code}")
            return []

        # Scansioniamo TUTTO il codice sorgente (anche il JS nascosto) cercando i raceid
        race_ids_trovati = re.findall(r'raceid=(\d+)', response.text, re.IGNORECASE)
        
        if not race_ids_trovati:
            # Piano B se i link sono formattati in JSON nel sorgente
            race_ids_trovati = re.findall(r'"raceId"\s*:\s*"?(\d+)"?', response.text, re.IGNORECASE)

        # Pulizia: rimuoviamo i duplicati ma manteniamo l'ordine in cui sono apparsi
        race_ids_unici = list(dict.fromkeys(race_ids_trovati))
        race_ids_finali = race_ids_unici[:limite_gare]
        
        print(f"🎯 Missione compiuta! Trovati {len(race_ids_finali)} ID gara univoci.")
        return race_ids_finali

    except Exception as e:
        print(f"❌ Errore di connessione al calendario: {e}")
        return []

# ==========================================
# ⚡ 4. ESTRATTORE VELOCE (Requests) - Analizza le singole gare
# ==========================================
def estrai_e_salva_gara(raceid):
    """Scarica i risultati statici di una gara in mezzo secondo e li spara su Supabase"""
    url = f"https://www.fis-ski.com/DB/general/results.html?sectorcode=CC&raceid={raceid}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    print(f"🚀 Elaborazione gara {raceid}...")
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"   ❌ Errore HTTP {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ Errore di rete sulla gara {raceid}: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # --- Estrazione Intestazione Gara (Luogo, Data, ecc.) ---
    try:
        luogo = soup.select_one(".event-header__name h1").text.strip() if soup.select_one(".event-header__name h1") else "N/D"
        data_gara = formatta_data_fis(soup.select_one(".date__full").text.strip() if soup.select_one(".date__full") else "N/D")
        categoria = soup.select_one(".event-header__kind").text.strip() if soup.select_one(".event-header__kind") else "FIS"
        specialita = soup.select_one(".event-header__subtitle").text.strip() if soup.select_one(".event-header__subtitle") else "Cross-Country"
    except Exception:
        luogo, data_gara, categoria, specialita = "N/D", datetime.datetime.now().strftime("%Y-%m-%d"), "FIS", "Cross-Country"

    # --- Estrazione Righe Atleti ---
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
            
            # Prendiamo tutti i blocchetti di testo delle colonne
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
            # Upsert fa in modo di aggiornare record esistenti senza creare duplicati
            supabase.table("Risultati_Fis").upsert(risultati_da_salvare).execute()
            print(f"   ✅ Salvati {len(risultati_da_salvare)} atleti: {luogo} | {specialita} | {data_gara}")
        except Exception as e:
            print(f"   ❌ Errore Supabase durante il salvataggio: {e}")

# ==========================================
# 🏁 5. AVVIO DELLO SCRIPT
# ==========================================
if __name__ == "__main__":
    print("=========================================")
    print("❄️ AVVIO FIS SCRAPER BOT (CROSS-COUNTRY) ❄️")
    print("=========================================\n")
    
    # 1. Trova le gare. Limite a 50 per prendere un bell'arco temporale
    gare_da_aggiornare = recupera_ultime_gare(limite_gare=50)
    
    if not gare_da_aggiornare:
        print("Nessuna gara trovata da processare. Termino lo script.")
        exit(0)

    # 2. Per ogni gara trovata, scarica e salva i risultati
    for id_gara in gare_da_aggiornare:
        estrai_e_salva_gara(id_gara)
        # Una pausa (1 secondo) per rispetto verso il server FIS
        time.sleep(1)
        
    print("\n🏆 Aggiornamento completato con successo! Tutti i dati sono su Supabase.")
