import os
import time
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
    print("--- 🌍 AVVIO SCRAPER FIS (BROWSER INVISIBILE) ---")
    
    # Apriamo il browser Chrome fantasma
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print(f"🔍 Apro il calendario e aspetto l'autorizzazione FIS...")
        page.goto(URL_CALENDARIO, timeout=60000)
        
        # IL TRUCCO: Aspettiamo 5 secondi che Javascript popoli la tabella!
        page.wait_for_timeout(5000) 
        
        # Ora prendiamo il codice della pagina caricata
        html = page.content()
        soup = BeautifulSoup(html, 'html.parser')
        
        link_gare = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            # I link FIS possono usare raceid o racecodex
            if 'raceid=' in href or 'racecodex=' in href:
                link_gare.append(href)
                
        link_gare = list(set(link_gare)) 
        print(f"🎯 BARRIERA SUPERATA! Trovate {len(link_gare)} gare FIS in Italia.\n")

        if len(link_gare) == 0:
            print("🛑 Il Javascript non si è caricato. Dobbiamo ritentare.")
            browser.close()
            return

        # FASE 2: Entro nelle gare (NE FACCIO SOLO 3 PER TEST)
        for link in link_gare[:3]:
            url_gara = BASE_URL + link if not link.startswith('http') else link
            
            if 'raceid=' in link:
                id_gara_fis = link.split('raceid=')[1].split('&')[0]
            elif 'racecodex=' in link:
                id_gara_fis = link.split('racecodex=')[1].split('&')[0]
            else:
                id_gara_fis = "N/D"
            
            print(f"⛷️ Analizzo gara FIS ID: {id_gara_fis}")
            page.goto(url_gara, timeout=60000)
            page.wait_for_timeout(3000) # Aspetto 3 secondi che carichi la classifica
            
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
                    except Exception as parse_e:
                        continue 
            
            if batch_risultati:
                supabase.table("Risultati_FIS").upsert(batch_risultati).execute()
                print(f"   ✅ Salvati {len(batch_risultati)} atleti nel database!")
            else:
                print("   ⚠️ Classifica non disponibile o formato sconosciuto.")
            
        print("\n🏁 TEST COMPLETATO!")
        browser.close()

if __name__ == "__main__":
    scraper_fis_master()
