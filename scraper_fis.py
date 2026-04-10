import os
import time
import requests
import datetime
import re
from bs4 import BeautifulSoup
from supabase import create_client
from playwright.sync_api import sync_playwright

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
# 🗺️ 3. RICOGNITORE (Playwright) - Legge il calendario dinamico
# ==========================================
def recupera_ultime_gare(limite_gare=15):
    """Apre il calendario, gestisce i cookie ed estrae i link usando selettori robusti"""
    print(f"🌍 Avvio il Ricognitore (browser fantasma) per leggere il calendario dinamico...")
    url_calendario = "https://www.fis-ski.com/DB/cross-country/calendar-results.html?eventselection=actualresults&sectorcode=CC&racedatetype=onp&include_at_least_one_results=true"
    
    race_ids = []
    
    try:
        with sync_playwright() as p:
            # headless=True è perfetto per server/GitHub Actions
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
            page = context.new_page()
            
            page.goto(url_calendario, wait_until="domcontentloaded", timeout=60000)
            
            # 🛡️ Chiudiamo il banner dei cookie se appare (spesso blocca il sito)
            try:
                page.click("#onetrust-accept-btn-handler", timeout=3000)
                print("🍪 Cookie accettati.")
            except:
                pass # Se non c'è, andiamo avanti tranquilli

            # 🎯 Il nuovo selettore infallibile: cerchiamo QUALSIASI link che contenga "raceid="
            print("⏳ Attendo il caricamento della griglia del calendario...")
            page.wait_for_selector("a[href*='raceid=']", timeout=20000)
            
            # Scrolliamo leggermente per far "svegliare" i link fuori dallo schermo (lazy loading)
            for _ in range(3):
                page.mouse.wheel(0, 1500)
                page.wait_for_timeout(1000)
                
            # Estraiamo tutti i link (href) trovati
            links = page.eval_on_selector_all("a[href*='raceid=']", "elements => elements.map(e => e.href)")
            
            for link in links:
                # Estraiamo solo il numero dell'ID tramite espressione regolare
                match = re.search(r'raceid=(\d+)', link, re.IGNORECASE)
                if match:
                    rid = match.group(1)
                    # Aggiungiamo alla lista solo se non c'è già, per evitare duplicati
                    if rid not in race_ids:
                        race_ids.append(rid)
                        
            browser.close()
    except Exception as e:
        print(f"❌ Errore durante l'esplorazione del calendario: {e}")
        
    # Tagliamo la lista al limite impostato (es. le ultime 15 gare)
    race_ids_finali = race_ids[:limite_gare]
    print(f"🎯 Missione compiuta! Trovati {len(race_ids_finali)} ID gara univoci: {race_ids_finali}\n")
    return race_ids_finali

# ==========================================
# ⚡ 4. ESTRATTORE VELOCE (Requests) - Analizza le singole gare
# ==========================================
def estrai_e_salva_gara(raceid):
    """Scarica i risultati statici in mezzo secondo e li spara su Supabase"""
    url = f"https://www.fis-ski.com/DB/general/results.html?sectorcode=CC&raceid={raceid}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    print(f"🚀 Elaborazione gara {raceid}...")
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"   ❌ Errore API: HTTP {response.status_code}")
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
    # (Qui usiamo .table-row perché nella pagina dei risultati la classe è corretta)
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
            # Upsert fa in modo di aggiornare record esistenti senza creare duplicati fastidiosi
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
    
    # 1. Trova le ultime 15 gare finite
    gare_da_aggiornare = recupera_ultime_gare(limite_gare=15)
    
    if not gare_da_aggiornare:
        print("Nessuna gara trovata da processare. Termino lo script.")
        exit(0)

    # 2. Per ogni gara trovata, scarica e salva i risultati
    for id_gara in gare_da_aggiornare:
        estrai_e_salva_gara(id_gara)
        # Una piccolissima pausa (mezzo secondo) per non farsi bannare dal server FIS
        time.sleep(0.5)
        
    print("\n🏆 Aggiornamento completato con successo! Tutti i dati sono su Supabase.")
