import os
import time
import datetime
from supabase import create_client
from playwright.sync_api import sync_playwright

# 🟢 INIZIALIZZAZIONE SUPABASE
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERRORE CRITICO: Variabili di ambiente Supabase mancanti!")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def estrai_dati_gara(page, url_gara):
    """Entra nella pagina della gara ed estrae la classifica"""
    print(f"   🔍 Analizzo classifica: {url_gara}")
    page.goto(url_gara, timeout=60000)
    time.sleep(3) # Diamo tempo al sito FIS di caricare la tabella dinamica

    risultati_da_salvare = []
    
    try:
        # Estrazione Dati Generali Gara (Testata)
        id_gara = url_gara.split("raceid=")[-1].split("&")[0]
        
        luogo_elem = page.locator(".event-header__name h1")
        luogo = luogo_elem.inner_text(timeout=5000).strip() if luogo_elem.count() > 0 else "N/D"
        
        data_elem = page.locator(".date__full")
        data_gara_raw = data_elem.inner_text().strip() if data_elem.count() > 0 else datetime.datetime.now().strftime("%d/%m/%Y")
        
        cat_elem = page.locator(".event-header__kind")
        categoria = cat_elem.inner_text().strip() if cat_elem.count() > 0 else "FIS"
        
        spec_elem = page.locator(".event-header__subtitle")
        specialita = spec_elem.inner_text().strip() if spec_elem.count() > 0 else "Cross-Country"

        # Troviamo tutte le righe
        righe_atleti = page.locator("a.table-row")
        numero_atleti = righe_atleti.count()
        print(f"   ⛷️ Analizzo {numero_atleti} righe trovate...")

        for i in range(numero_atleti):
            riga = righe_atleti.nth(i)
            
            # 1. Cerchiamo il Codice FIS (Deve essere un numero!)
            try: codice_fis = riga.locator(".g-md-1").first.inner_text().strip()
            except: codice_fis = ""
            
            # 🛡️ IL BUTTAFUORI: Se non c'è un codice FIS numerico, NON è un atleta!
            # Scarta in automatico indirizzi, nomi di società, o righe spurie (es. "Via Manzoni")
            if not codice_fis.isdigit() or len(codice_fis) < 5:
                continue 

            # 2. Estrazione Posizione
            try: posizione = riga.locator(".pr-1").first.inner_text().strip()
            except: posizione = str(i+1)
            
            # 3. Estrazione Nome (Miriamo solo alla colonna larga dedicata ai nomi)
            try: 
                nome_elem = riga.locator(".g-lg-4, .g-md-4").first
                atleta_nome = nome_elem.inner_text().strip()
            except: 
                atleta_nome = "Sconosciuto"
            
            # 4. Estrazione Nazione
            try: nazione = riga.locator(".country__name-short").first.inner_text().strip()
            except: nazione = "N/D"
            
            # 5. Estrazione Tempo e Punti
            try: tempo = riga.locator(".justify-content-end.pr-1").first.inner_text().strip()
            except: tempo = "N/D"
            
            try: punti_fis = riga.locator(".pl-1.g-sm-1").first.inner_text().strip()
            except: punti_fis = "0.00"

            record = {
                "id_gara_fis": id_gara,
                "data_gara": data_gara_raw,
                "luogo": luogo,
                "posizione": posizione,
                "codice_fis": codice_fis,
                "atleta_nome": atleta_nome.replace("\n", " "), # Pulisce eventuali a capo sporchi
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
        print(f"   ⚠️ Errore nell'estrazione della gara {url_gara}: {e}")

    return risultati_da_salvare


def avvia_scraper_fis():
    print("--- 🚀 AVVIO BOT SCRAPER FIS (CROSS-COUNTRY) ---", flush=True)
    
    # 🎯 Includiamo i mesi di fine 2025 (inizio stagione) e inizio 2026 (fine stagione)
    mesi_da_cercare = ["11-2025", "12-2025", "01-2026", "02-2026", "03-2026"]
    totale_salvati = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()

        for mese in mesi_da_cercare:
            print(f"\n🌍 Mi collego al calendario FIS (Mese: {mese})...")
            # seasoncode=2026 copre l'intera stagione agonistica, seasonmonth filtra il mese specifico
            url_mese = f"https://www.fis-ski.com/DB/cross-country/calendar-results.html?sectorcode=CC&seasoncode=2026&seasonmonth={mese}"
            
            try:
                page.goto(url_mese, timeout=60000)
                time.sleep(3)
                
                # Gestione Cookie
                if page.locator("#onetrust-accept-btn-handler").count() > 0:
                    page.locator("#onetrust-accept-btn-handler").click()
                    time.sleep(1)

                print("⏳ Faccio scroll verso il basso per ingannare il sito...")
                # Scrolliamo la pagina un paio di volte simulando un utente umano per far caricare i link
                for _ in range(5):
                    page.evaluate("window.scrollBy(0, 1000)")
                    time.sleep(1)

                print("⏳ Aspetto i link delle gare (Pazienza 30s)...")
                page.wait_for_selector("a[href*='raceid=']", timeout=30000)

                # Raccogliamo i link
                link_elementi = page.locator("a[href*='raceid=']")
                numero_link = link_elementi.count()
                
                url_gare_trovate = set()
                for i in range(numero_link):
                    href = link_elementi.nth(i).get_attribute("href")
                    if href:
                        url_completo = href if href.startswith("http") else f"https://www.fis-ski.com{href}"
                        url_gare_trovate.add(url_completo)
                
                print(f"🎯 Trovate {len(url_gare_trovate)} gare nel mese {mese}.")

                # Analizziamo le singole gare
                for url in url_gare_trovate:
                    risultati = estrai_dati_gara(page, url)
                    if risultati:
                        try:
                            supabase.table("Risultati_Fis").upsert(risultati).execute()
                            totale_salvati += len(risultati)
                            print(f"   ✅ Salvati {len(risultati)} atleti.")
                        except Exception as e:
                            print(f"   ❌ Errore Supabase: {e}")
                    time.sleep(2)

            except Exception as e:
                print(f"⚠️ Nessuna gara trovata per {mese} o la pagina ci ha bloccato. Passo al mese successivo.")

        browser.close()
        print(f"\n🏆 SCRAPING COMPLETATO! Totale atleti aggiornati: {totale_salvati}", flush=True)

if __name__ == "__main__":
    avvia_scraper_fis()
