from playwright.sync_api import sync_playwright
import json

# Il nostro target specifico
URL_GARA = "https://www.fis-ski.com/DB/general/results.html?sectorcode=CC&raceid=50468"

def intercetta_traffico_api():
    print(f"🕵️ Avvio radar di rete per la gara 50468...")
    print("In attesa delle chiamate API in background...\n")

    with sync_playwright() as p:
        # Usiamo headless=False così vedi se c'è un blocco cookie o Cloudflare
        # CORRETTO (per GitHub Actions)
         browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # Funzione che scansiona ogni singola risposta di rete
        def analizza_risposta(response):
            # Vogliamo solo le risposte con successo (200) e che contengono JSON
            if response.status == 200:
                content_type = response.headers.get("content-type", "")
                
                # Molte API restituiscono application/json, a volte text/plain
                if "json" in content_type.lower():
                    url = response.url
                    
                    # Filtriamo via roba inutile (tracciamenti, analytics, ecc.)
                    # Ci interessano le chiamate che contengono il raceid o parole chiave della FIS
                    if "50468" in url or "api" in url.lower() or "results" in url.lower():
                        print("=" * 60)
                        print(f"🚨 TROVATO POSSIBILE ENDPOINT API! 🚨")
                        print(f"🔗 URL: {url}")
                        
                        try:
                            # Estraiamo il body in JSON
                            dati = response.json()
                            print(f"📦 Tipo di dato: {type(dati)}")
                            
                            # Stampiamo le chiavi principali o un'anteprima
                            if isinstance(dati, dict):
                                print(f"🔑 Chiavi principali: {list(dati.keys())}")
                                print("\n📄 Anteprima primi 300 caratteri:")
                                print(json.dumps(dati, indent=2)[:300] + "\n...")
                            elif isinstance(dati, list):
                                print(f"🔢 È una lista di {len(dati)} elementi.")
                                if len(dati) > 0:
                                    print("\n📄 Anteprima primo elemento:")
                                    print(json.dumps(dati[0], indent=2)[:300] + "\n...")
                        except Exception as e:
                            print(f"⚠️ Impossibile leggere il JSON: {e}")
                        print("=" * 60 + "\n")

        # Agganciamo il nostro "ascoltatore" alla pagina
        page.on("response", analizza_risposta)
        
        # Navighiamo verso la pagina
        try:
            page.goto(URL_GARA, wait_until="domcontentloaded", timeout=60000)
            
            # Simuliamo l'interazione per far triggerare il caricamento dei risultati
            page.wait_for_timeout(3000)
            for _ in range(3):
                page.mouse.wheel(0, 1500)
                page.wait_for_timeout(1000)
                
        except Exception as e:
            print(f"Errore di navigazione: {e}")

        browser.close()
        print("🛑 Scansione terminata.")

if __name__ == "__main__":
    intercetta_traffico_api()
