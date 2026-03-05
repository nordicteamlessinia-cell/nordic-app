import os
from bs4 import BeautifulSoup
from supabase import create_client
from playwright.sync_api import sync_playwright

# 🔑 INIZIALIZZA SUPABASE 
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("⚠️ ERRORE: Variabili d'ambiente Supabase mancanti!")
    exit()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BASE_URL = "https://www.fis-ski.com"
URL_CALENDARIO = f"{BASE_URL}/DB/cross-country/calendar-results.html?sectorcode=CC&nationcode=ita&seasoncode=2026"

def scraper_fis_master():
    print("--- 🌍 AVVIO SCRAPER FIS (MODALITÀ MATRIOSKA) ---")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # 📦 LIVELLO 1: IL CALENDARIO (Cerco gli Eventi)
        print("🔍 Apro il calendario e cerco gli 'Eventi'...")
        page.goto(URL_CALENDARIO, timeout=60000)
        page.wait_for_timeout(5000) 
        soup = BeautifulSoup(page.content(), 'html.parser')
        
        link_eventi = []
        for a in soup.find_all('a', href=True):
            if 'eventid=' in a['href']:
                link_eventi.append(a['href'])
                
        link_eventi = list(set(link_eventi)) 
        print(f"🎟️ Trovati {len(link_eventi)} Eventi FIS in Italia.")

        if not link_eventi:
            print("🛑 Nessun evento trovato. Esco.")
            browser.close()
            return

        # 📦 LIVELLO 2: L'EVENTO (Cerco le Gare)
        link_gare = []
        print("\nEntro negli eventi per cercare le singole gare...")
        
        # ⚠️ TEST: Controllo solo i primi 2 Eventi per fare in fretta
        for ev in link_eventi[:2]: 
            url_ev = BASE_URL + ev if not ev.startswith('http') else ev
            print(f"   ➡️ Apro Evento...")
            page.goto(url_ev, timeout=60000)
            page.wait_for_timeout(3000)
            
            ev_soup = BeautifulSoup(page.content(), 'html.parser')
            for a in ev_soup.find_all('a', href=True):
                # Ora cerco i risultati delle singole gare!
                if 'raceid=' in a['href']:
                    link_gare.append(a['href'])
                    
        link_gare = list(set(link_gare))
        print(f"🎯 JACKPOT! Trovate {len(link_gare)} singole gare in questi eventi.\n")

        # 📦 LIVELLO 3: LA GARA (Estraggo gli Atleti)
        # ⚠️ TEST: Controllo solo le prime 2 gare
        for link in link_gare[:2]: 
            url_gara = BASE_URL + link if not link.startswith('http') else link
            id_gara_fis = link.split('raceid=')[1].split('&')[0] if 'raceid=' in link else "N/D"
            
            print(f"⛷️ Analizzo Gara FIS ID: {id_gara_fis}")
            page.goto(url_gara, timeout=60000)
            page.wait_for_timeout(3000)
            
            gara_soup = BeautifulSoup(page.content(), 'html.parser')
            titolo_gara = gara_soup.find('h1').text.strip() if gara_soup.find('h1') else "Gara FIS"
            
            righe_atleti = gara_soup.find_all('div', class_='g-row')
            if not righe_atleti:
                righe_atleti = gara_soup.find_all('a', class_='pr-1')
                
            batch_risultati = []
            
            for riga in righe_atleti:
                testi = [t.strip() for t in riga.stripped_strings if t.strip()]
                if len(testi) >= 5:
                    try:
                        codice_fis = next((t for t in testi if len(t) >= 6 and t.isdigit()), "N/D")
                        tempo = next((t for t in testi if ":" in t), "N/D")
                        punti_str = next((t for t in reversed(testi) if "." in t and t.replace('.','',1).isdigit()), "0.00")
                        
                        nome = "N/D"
                        for t in testi:
                            if not t.isdigit() and ":" not in t and "." not in t and len(t) > 4 and t != "ITA":
                                nome = t
                                break
                                
                        nazione = "ITA" if "ITA" in testi else "N/D"
                        posizione_pulita = int(testi[0]) if testi[0].isdigit() else None
                        punti_puliti = float(punti_str) if punti_str != "0.00" else None

                        batch_risultati.append({
                            "id_gara_fis": id_gara_fis,
                            "data_gara": "2026",
                            "luogo": "Italia",
                            "posizione": posizione_pulita,
                            "codice_fis": codice_fis,
                            "atleta_nome": nome,
                            "nazione": nazione,
                            "tempo": tempo,
                            "punti_fis": punti_puliti,
                            "categoria": titolo_gara
                        })
                    except:
                        continue 
            
            if batch_risultati:
                supabase.table("Risultati_FIS").upsert(batch_risultati).execute()
                print(f"   ✅ Salvati {len(batch_risultati)} atleti!")
            else:
                print("   ⚠️ Nessun atleta trovato con il formato atteso.")
                
        print("\n🏁 TEST COMPLETATO!")
        browser.close()

if __name__ == "__main__":
    scraper_fis_master()
