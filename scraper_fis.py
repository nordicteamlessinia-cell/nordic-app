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

# 🕰️ GLI ANNI CHE VOGLIAMO SCARICARE
STAGIONI = ["2023", "2024", "2025", "2026"]

def scraper_fis_master():
    print("--- 🌍 AVVIO SCRAPER FIS (STORICO COMPLETO) ---")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        for stagione in STAGIONI:
            print(f"\n==========================================")
            print(f"🎿 INIZIO SCANSIONE STAGIONE: {stagione}")
            print(f"==========================================")
            
            URL_CALENDARIO = f"{BASE_URL}/DB/cross-country/calendar-results.html?sectorcode=CC&nationcode=ita&seasoncode={stagione}"
            
            # 📦 LIVELLO 1: IL CALENDARIO (Cerco gli Eventi)
            print(f"🔍 Apro il calendario {stagione}...")
            page.goto(URL_CALENDARIO, timeout=60000)
            page.wait_for_timeout(5000) 
            soup = BeautifulSoup(page.content(), 'html.parser')
            
            link_eventi = []
            for a in soup.find_all('a', href=True):
                if 'eventid=' in a['href']:
                    link_eventi.append(a['href'])
                    
            link_eventi = list(set(link_eventi)) 
            print(f"🎟️ Trovati {len(link_eventi)} Eventi.")

            if not link_eventi:
                print(f"🛑 Nessun evento trovato per il {stagione}. Passo al prossimo anno.")
                continue

            # 📦 LIVELLO 2: L'EVENTO (Cerco le Gare)
            link_gare = []
            for ev in link_eventi: 
                url_ev = BASE_URL + ev if not ev.startswith('http') else ev
                page.goto(url_ev, timeout=60000)
                page.wait_for_timeout(2000)
                
                ev_soup = BeautifulSoup(page.content(), 'html.parser')
                for a in ev_soup.find_all('a', href=True):
                    if 'raceid=' in a['href']:
                        link_gare.append(a['href'])
                        
            link_gare = list(set(link_gare))
            print(f"🎯 Trovate {len(link_gare)} singole gare nel {stagione}.\n")

            # 📦 LIVELLO 3: LA GARA (Estraggo gli Atleti)
            for link in link_gare: 
                url_gara = BASE_URL + link if not link.startswith('http') else link
                id_gara_fis = link.split('raceid=')[1].split('&')[0] if 'raceid=' in link else "N/D"
                
                print(f"⛷️ Analizzo Gara FIS ID: {id_gara_fis} ({stagione})")
                page.goto(url_gara, timeout=60000)
                page.wait_for_timeout(2500)
                
                gara_soup = BeautifulSoup(page.content(), 'html.parser')
                
                # --- 🎯 NUOVA ESTRAZIONE DI PRECISIONE ---
                # 1. Il Luogo (Di solito è l'H1 principale, es. "Toblach (ITA)")
                h1 = gara_soup.find('h1')
                luogo = h1.text.strip() if h1 else "Italia"
                
                # 2. La Data (Cerchiamo tag con classi che contengono 'date')
                data_gara = stagione # Valore di riserva
                for tag in gara_soup.find_all(['span', 'div', 'p']):
                    if any('date' in str(c).lower() for c in tag.get('class', [])):
                        data_gara = tag.text.strip()
                        break
                
                # 3. La Specialità (Cerchiamo sottotitoli o 'kind')
                specialita = "Gara FIS"
                for tag in gara_soup.find_all(['span', 'div', 'p', 'h2', 'h3']):
                    classi = str(tag.get('class', [])).lower()
                    if 'kind' in classi or 'subtitle' in classi or 'event-header__name' in classi:
                        specialita = tag.text.strip()
                        break
                if specialita == "Gara FIS" and gara_soup.find('h2'):
                    specialita = gara_soup.find('h2').text.strip()
                # -----------------------------------------

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
                                "data_gara": data_gara,         # Adesso usa la data vera!
                                "luogo": luogo,                 # Adesso usa la città
                                "posizione": posizione_pulita,
                                "codice_fis": codice_fis,
                                "atleta_nome": nome,
                                "nazione": nazione,
                                "tempo": tempo,
                                "punti_fis": punti_puliti,
                                "categoria": "FIS Cross-Country", # Generico, la specialità la mettiamo a parte
                                "specialita": specialita        # Adesso estrae "10km Free", "Sprint", ecc.
                            })
                        except:
                            continue 
                
                if batch_risultati:
                    supabase.table("Risultati_Fis").upsert(batch_risultati).execute()
                    print(f"   ✅ Salvati {len(batch_risultati)} atleti!")
                else:
                    print("   ⚠️ Nessun atleta o formato non standard.")
                    
        print("\n🏁 DATABASE STORICO AGGIORNATO CON SUCCESSO!")
        browser.close()

if __name__ == "__main__":
    scraper_fis_master()
