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
    print("--- 🌍 AVVIO SCRAPER FIS (MOTORE SEMANTICO) ---")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        for stagione in STAGIONI:
            print(f"\n==========================================")
            print(f"🎿 INIZIO SCANSIONE STAGIONE: {stagione}")
            print(f"==========================================")
            
            URL_CALENDARIO = f"{BASE_URL}/DB/cross-country/calendar-results.html?sectorcode=CC&nationcode=ita&seasoncode={stagione}"
            
            page.goto(URL_CALENDARIO, timeout=60000)
            page.wait_for_timeout(5000) 
            soup = BeautifulSoup(page.content(), 'html.parser')
            
            link_eventi = []
            for a in soup.find_all('a', href=True):
                if 'eventid=' in a['href']:
                    link_eventi.append(a['href'])
                    
            link_eventi = list(set(link_eventi)) 
            if not link_eventi:
                continue

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
            print(f"🎯 Trovate {len(link_gare)} gare nel {stagione}.\n")

            for link in link_gare: 
                url_gara = BASE_URL + link if not link.startswith('http') else link
                id_gara_fis = link.split('raceid=')[1].split('&')[0] if 'raceid=' in link else "N/D"
                
                print(f"⛷️ Analizzo Gara ID: {id_gara_fis}")
                page.goto(url_gara, timeout=60000)
                page.wait_for_timeout(2500)
                
                gara_soup = BeautifulSoup(page.content(), 'html.parser')
                
                # --- 🧠 MOTORE SEMANTICO DI ESTRAZIONE ---
                luogo = "Italia"
                data_gara = stagione
                specialita = "N/D"
                categoria = "FIS" # Valore di default
                
                # 1. IL LUOGO (H1) -> Di solito è pulito, es: "Toblach (ITA)"
                h1 = gara_soup.find('h1')
                if h1:
                    luogo = h1.text.replace("junior", "").replace("Junior", "").strip()
                
                # Raccogliamo tutto il testo dell'intestazione per analizzarlo
                header_texts = []
                for tag in gara_soup.find_all(['h1', 'h2', 'h3', 'div', 'span', 'p']):
                    testo = tag.get_text(separator=" ", strip=True)
                    if testo and len(testo) < 60 and testo not in header_texts:
                        header_texts.append(testo)
                
                # Leggiamo i testi come un essere umano
                for testo in header_texts:
                    t_low = testo.lower()
                    
                    # 🎯 Trova la DISCIPLINA (se contiene km, sprint, mass start, ecc.)
                    if any(x in t_low for x in ['km', 'sprint', 'skiathlon', 'pursuit', 'mass start', 'relay']):
                        if specialita == "N/D":
                            specialita = testo
                            
                    # 🎯 Trova la CATEGORIA in modo esatto
                    if 'junior' in t_low:
                        categoria = "Junior"
                    elif 'u23' in t_low:
                        categoria = "U23"
                    elif 'world cup' in t_low:
                        categoria = "World Cup"
                    elif 'alpen' in t_low or 'opa' in t_low:
                        categoria = "Alpen Cup / OPA"
                    elif 'championship' in t_low:
                        categoria = "Championship"
                    elif 'national' in t_low:
                        categoria = "National Race"
                        
                    # 🎯 Trova la DATA
                    elif any(month in t_low for month in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec', '2023', '2024', '2025', '2026']):
                        if any(char.isdigit() for char in testo) and len(testo) < 20:
                            data_gara = testo
                # ----------------------------------------

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
                                "data_gara": data_gara,
                                "luogo": luogo,
                                "posizione": posizione_pulita,
                                "codice_fis": codice_fis,
                                "atleta_nome": nome,
                                "nazione": nazione,
                                "tempo": tempo,
                                "punti_fis": punti_puliti,
                                "categoria": categoria,      # ⬅️ ORA È CORRETTA!
                                "specialita": specialita     # ⬅️ ORA PRENDE I KM / SPRINT!
                            })
                        except:
                            continue 
                
                if batch_risultati:
                    supabase.table("Risultati_Fis").upsert(batch_risultati).execute()
                    print(f"   ✅ Salvati {len(batch_risultati)} atleti | Cat: {categoria} | Disp: {specialita}")
                else:
                    print("   ⚠️ Nessun atleta o formato non standard.")
                    
        print("\n🏁 DATABASE STORICO AGGIORNATO CON SUCCESSO!")
        browser.close()

if __name__ == "__main__":
    scraper_fis_master()
