import os
import time
from playwright.sync_api import sync_playwright

def auto_scroll(page):
    """Scorre la pagina fino in fondo per attivare il lazy loading della FIS"""
    previous_height = page.evaluate("document.body.scrollHeight")
    while True:
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        page.wait_for_timeout(2000) # Attesa per il rendering del nuovo chunk
        new_height = page.evaluate("document.body.scrollHeight")
        if new_height == previous_height:
            break
        previous_height = new_height

def avvia_scraper_fis_pro():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()

        # URL OTTIMIZZATO: Filtro Cross-Country + Nazione Italia + Risultati presenti
        url_ita = (
            "https://www.fis-ski.com/DB/cross-country/calendar-results.html?"
            "eventselection=actualresults&sectorcode=CC&nationcode=ITA&"
            "racedatetype=onp&include_at_least_one_results=true"
        )

        print(f"🌍 Navigo su: {url_ita}")
        page.goto(url_ita, wait_until="domcontentloaded")
        
        # Aspettiamo che la tabella principale sia caricata
        try:
            page.wait_for_selector(".table-row", timeout=20000)
        except:
            print("❌ Nessuna gara trovata con questi filtri.")
            return

        # 1. Carichiamo tutti i link (Lazy Loading)
        auto_scroll(page)

        # 2. Estrazione Link Univoci
        # Usiamo un selettore più preciso: l'anchor che contiene il raceid
        gare_links = page.eval_on_selector_all(
            "a[href*='raceid=']", 
            "elements => elements.map(e => e.href)"
        )
        
        # Pulizia duplicati (la FIS spesso mette il link sia sulla riga che sulla freccia)
        url_unici = list(dict.fromkeys(gare_links))
        print(f"🎯 Gare Italiane trovate: {len(url_unici)}")

        for url in url_unici:
            processa_classifica_gara(page, url)

        browser.close()

def processa_classifica_gara(page, url):
    """Logica di estrazione dei singoli atleti con selettori robusti"""
    page.goto(url, wait_until="domcontentloaded")
    
    # Aspettiamo che il loader sparisca (fondamentale su FIS-ski)
    page.wait_for_selector(".table-row", timeout=15000)
    
    # Esempio di estrazione "robusta" senza classi numeriche
    rows = page.locator(".table-row")
    for i in range(rows.count()):
        row = rows.nth(i)
        
        # Estraiamo i dati usando la posizione relativa (più stabile delle classi .g-lg-X)
        try:
            # Il nome dell'atleta è l'unico con classe .athlete-name
            nome = row.locator(".athlete-name").inner_text().strip()
            # La nazione è sempre dentro .country__name-short
            nazione = row.locator(".country__name-short").inner_text().strip()
            # Il tempo è solitamente l'ultimo elemento prima dei punti
            # Usiamo filtri CSS intelligenti o regex se necessario
            
            print(f"   ⛷️ Atleta: {nome} ({nazione})")
            # Qui andrebbe il salvataggio su Supabase...
        except:
            continue

if __name__ == "__main__":
    avvia_scraper_fis_pro()
