import os
import time
import datetime
import re
from supabase import create_client
from playwright.sync_api import sync_playwright

# --- CONFIGURAZIONE ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def formatta_data_fis(testo_data):
    """Converte date tipo 'March 24, 2024' o '24-03-2024' in '2024-03-24'"""
    try:
        # Rimuove eventuali newline o spazi extra
        clean_date = testo_data.split('\n')[0].strip()
        # Prova il parsing standard
        for fmt in ("%B %d, %Y", "%d %b %Y", "%d.%m.%Y", "%Y-%m-%d"):
            try:
                return datetime.datetime.strptime(clean_date, fmt).strftime("%Y-%m-%d")
            except:
                continue
        return datetime.datetime.now().strftime("%Y-%m-%d")
    except:
        return datetime.datetime.now().strftime("%Y-%m-%d")

def estrai_dati_gara(page, url_gara):
    """Entra nella pagina della gara ed estrae la classifica"""
    print(f"   🔍 Analizzo classifica: {url_gara}")
    try:
        page.goto(url_gara, wait_until="networkidle", timeout=60000)
        page.wait_for_selector(".table-row", timeout=10000)
    except:
        print(f"   ⚠️ Timeout o nessun dato trovato per {url_gara}")
        return []

    risultati_da_salvare = []
    
    try:
        # Estrazione Dati Testata
        id_gara = url_gara.split("raceid=")[-1].split("&")[0]
        luogo = page.locator(".event-header__name h1").first.inner_text().strip() if page.locator(".event-header__name h1").count() > 0 else "N/D"
        
        data_raw = page.locator(".date__full").first.inner_text().strip() if page.locator(".date__full").count() > 0 else ""
        data_pulita = formatta_data_fis(data_raw)
        
        categoria = page.locator(".event-header__kind").first.inner_text().strip() if page.locator(".event-header__kind").count() > 0 else "FIS"
        specialita = page.locator(".event-header__subtitle").first.inner_text().strip() if page.locator(".event-header__subtitle").count() > 0 else "Cross-Country"

        # Selettore righe atleti (la classe table-row è la più affidabile)
        righe = page.locator("a.table-row")
        count = righe.count()
        print(f"   ⛷️ Trovati {count} atleti.")

        for i in range(count):
            riga = righe.nth(i)
            
            # Estrazione con selettori CSS diretti e fallback
            try:
                # La posizione è spesso nel primo div con classe 'pr-1' o simile
                pos = riga.locator(".g-lg-1.g-md-1.g-sm-1").first.inner_text().strip()
                fis_code = riga.locator(".g-lg-2.g-md-2.g-sm-3").first.inner_text().strip()
                nome = riga.locator(".athlete-name").first.inner_text().strip()
                naz = riga.locator(".country__name-short").first.inner_text().strip()
                tempo = riga.locator(".g-lg-2.g-md-3.g-sm-3.justify-content-end").first.inner_text().strip()
                punti = riga.locator(".g-lg-2.hidden-md-down").last.inner_text().strip()
                
                record = {
                    "id_gara_fis": id_gara,
                    "data_gara": data_pulita,
                    "luogo": luogo,
                    "posizione": pos,
                    "codice_fis": fis_code,
                    "atleta_nome": nome.replace("\n", " "),
                    "nazione": naz,
                    "tempo": tempo,
                    "punti_fis": punti if punti else "0.00",
                    "categoria": categoria,
                    "specialita": specialita,
                    "comitato": "FIS"
                }
                risultati_da_salvare.append(record)
            except Exception as row_err:
                continue # Salta riga se corrotta
                
    except Exception as e:
        print(f"   ⚠️ Errore generale nella pagina: {e}")

    return risultati_da_salvare

def avvia_scraper_fis():
    print("--- 🚀 AVVIO BOT SCRAPER FIS ---", flush=True)
    
    with sync_playwright() as p:
        # headless=True per produzione, False per vedere cosa succede
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 800}
        )
        page = context.new_page()

        # URL FILTRATO: Solo gare con risultati presenti (Cross-Country)
        url_base = "https://www.fis-ski.com/DB/cross-country/calendar-results.html?eventselection=actualresults&sectorcode=CC&racedatetype=onp&include_at_least_one_results=true"
        
        print("🌍 Navigo verso i risultati recenti...")
        page.goto(url_base, wait_until="networkidle")
        
        # Accetta i cookies se presenti
        try:
            page.click("#onetrust-accept-btn-handler", timeout=5000)
        except:
            pass

        # Scroll per caricare i risultati dinamici
        page.evaluate("window.scrollBy(0, 1000)")
        time.sleep(2)

        # Raccogliamo i link delle gare
        link_locators = page.locator("a.table-row")
        urls = []
        for i in range(link_locators.count()):
            href = link_locators.nth(i).get_attribute("href")
            if href and "raceid=" in href:
                full_url = href if href.startswith("http") else f"https://www.fis-ski.com{href}"
                if full_url not in urls:
                    urls.append(full_url)

        # Prendiamo solo le ultime 10 gare per efficienza (modificabile)
        url_finali = urls[:10]
        print(f"🎯 Gare identificate da processare: {len(url_finali)}")

        totale_aggiornati = 0
        for url in url_finali:
            dati = estrai_dati_gara(page, url)
            if dati:
                try:
                    # Inserimento su Supabase
                    res = supabase.table("Risultati_Fis").upsert(dati).execute()
                    totale_aggiornati += len(dati)
                    print(f"   ✅ Database aggiornato per questa gara.")
                except Exception as db_err:
                    print(f"   ❌ Errore Supabase: {db_err}")
            
            time.sleep(2) # Rispetto per il server

        browser.close()
        print(f"\n🏆 FINE. Totale record processati: {totale_aggiornati}")

if __name__ == "__main__":
    avvia_scraper_fis()
