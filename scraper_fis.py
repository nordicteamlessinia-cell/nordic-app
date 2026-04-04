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
        luogo = page.locator(".event-header__name h1").inner_text(timeout=5000).strip() if page.locator(".event-header__name h1").count() > 0 else "N/D"
        data_gara_raw = page.locator(".date__full").inner_text().strip() if page.locator(".date__full").count() > 0 else datetime.datetime.now().strftime("%d/%m/%Y")
        categoria = page.locator(".event-header__kind").inner_text().strip() if page.locator(".event-header__kind").count() > 0 else "FIS"
        specialita = page.locator(".event-header__subtitle").inner_text().strip() if page.locator(".event-header__subtitle").count() > 0 else "Cross-Country"

        # Troviamo tutte le righe degli atleti
        righe_atleti = page.locator("a.table-row")
        numero_atleti = righe_atleti.count()
        print(f"   ⛷️ Trovati {numero_atleti} atleti in classifica.")

        for i in range(numero_atleti):
            riga = righe_atleti.nth(i)
            
            # Estrazione sicura dei dati dalla riga (try/except inline per evitare blocchi se manca un dato)
            try: posizione = riga.locator(".pr-1").inner_text().strip()
            except: posizione = str(i+1)
            
            try: codice_fis = riga.locator(".g-md-1").inner_text().strip()
            except: codice_fis = "N/D"
            
            try: atleta_nome = riga.locator(".justify-content-md-start").inner_text().strip()
            except: atleta_nome = "Sconosciuto"
            
            try: nazione = riga.locator(".country__name-short").inner_text().strip()
            except: nazione = "N/D"
            
            try: tempo = riga.locator(".justify-content-end.pr-1").inner_text().strip()
            except: tempo = "N/D"
            
            try: punti_fis = riga.locator(".pl-1.g-sm-1").inner_text().strip()
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
                "nome_comitato": "Internazionale", # Valore fisso per le gare FIS
                "comitato": "Internazionale"       # Valore fisso per le gare FIS
            }
            risultati_da_salvare.append(record)
            
    except Exception as e:
        print(f"   ⚠️ Errore nell'estrazione della gara {url_gara}: {e}")

    return risultati_da_salvare


def avvia_scraper_fis():
    print("--- 🚀 AVVIO BOT SCRAPER FIS (CROSS-COUNTRY) ---", flush=True)
    
    with sync_playwright() as p:
        # Avviamo il browser fantasma
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # 1. Andiamo sul calendario FIS Cross-Country
        print("🌍 Mi collego al calendario FIS ufficiale...")
        page.goto("https://www.fis-ski.com/DB/cross-country/calendar-results.html", timeout=60000)
        
        # Gestione Popup Cookie (se appare, lo clicchiamo per non averlo tra i piedi)
        if page.locator("#onetrust-accept-btn-handler").count() > 0:
            page.locator("#onetrust-accept-btn-handler").click()
            time.sleep(1)

        # 2. Raccogliamo i link delle gare recenti
        # Cerchiamo tutti i link che portano a una classifica (contengono "raceid")
        link_elementi = page.locator("a[href*='raceid=']")
        numero_link = link_elementi.count()
        
        url_gare_trovate = set()
        for i in range(numero_link):
            href = link_elementi.nth(i).get_attribute("href")
            if href:
                # Costruiamo l'URL completo
                url_completo = href if href.startswith("http") else f"https://www.fis-ski.com{href}"
                url_gare_trovate.add(url_completo)
        
        print(f"🎯 Trovate {len(url_gare_trovate)} gare nel calendario attuale.")

        # 3. Analizziamo ogni gara e salviamo su Supabase
        totale_salvati = 0
        for url in url_gare_trovate:
            risultati = estrai_dati_gara(page, url)
            
            if risultati:
                # Salvataggio su Supabase
                try:
                    # Usiamo upsert per non creare doppioni se il bot gira due volte
                    supabase.table("Risultati_Fis").upsert(risultati).execute()
                    totale_salvati += len(risultati)
                    print(f"   ✅ Salvati {len(risultati)} atleti per questa gara nel database.")
                except Exception as e:
                    print(f"   ❌ Errore durante il salvataggio su Supabase: {e}")
            
            time.sleep(2) # Pausa di cortesia per non bombardare i server FIS

        browser.close()
        print(f"\n🏆 SCRAPING COMPLETATO! Totale atleti aggiornati oggi: {totale_salvati}", flush=True)

if __name__ == "__main__":
    avvia_scraper_fis()
