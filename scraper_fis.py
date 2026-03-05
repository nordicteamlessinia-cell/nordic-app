import os
import requests
import time
from bs4 import BeautifulSoup
from supabase import create_client

# 🔑 INIZIALIZZA SUPABASE 
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("⚠️ ERRORE: Variabili d'ambiente Supabase mancanti. Impostale prima di lanciare lo script!")
    exit()

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BASE_URL = "https://www.fis-ski.com"
# Ho corretto il parametro in seasoncode per fargli digerire l'anno
URL_CALENDARIO = f"{BASE_URL}/DB/cross-country/calendar-results.html?sectorcode=CC&nationcode=ita&seasoncode=2026"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, come Gecko) Chrome/122.0.0.0 Safari/537.36'
}

def scraper_fis_master():
    print("--- 🌍 AVVIO SCRAPER FIS (ITALIA - 2026) ---")
    
    try:
        print(f"🔍 Cerco le gare al link: {URL_CALENDARIO}")
        res = requests.get(URL_CALENDARIO, headers=HEADERS, timeout=15)
        
        # Testiamo se la FIS ci sta mettendo un muro davanti
        if res.status_code != 200:
            print(f"❌ La FIS ci ha bloccato con un errore: {res.status_code}")
            return

        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Estraggo letteralmente TUTTI i link della pagina
        tutti_i_link = soup.find_all('a', href=True)
        print(f"📡 Radar: Il sito ha risposto. Trovati {len(tutti_i_link)} link generici nella pagina.")
        
        if len(tutti_i_link) < 20:
             print("⚠️ ATTENZIONE: Pochissimi link! Probabile blocco anti-bot o caricamento JavaScript attivo.")
             print(f"Anteprima testo pagina: {soup.text[:300]}")
        
        link_gare = []
        for a in tutti_i_link:
            href = a.get('href', '')
            # Adesso cerchiamo SOLO 'raceid=', senza farci ingannare da altri pezzi di link
            if 'raceid=' in href:
                link_gare.append(href)
                
        link_gare = list(set(link_gare)) # Rimuovo i duplicati
        print(f"🎯 Trovate {len(link_gare)} gare FIS in Italia. Inizio l'estrazione...\n")

        if len(link_gare) == 0:
            print("🛑 Mi fermo qui: Nessun link con 'raceid=' trovato. Devo analizzare i dati grezzi.")
            return

        # FASE 2: Entro in ogni singola gara
        for link in link_gare:
            url_gara = BASE_URL + link if not link.startswith('http') else link
            id_gara_fis = link.split('raceid=')[1].split('&')[0] if 'raceid=' in link else "N/D"
            
            print(f"⛷️ Analizzo gara FIS ID: {id_gara_fis}")
            
            try:
                r_gara = requests.get(url_gara, headers=HEADERS, timeout=15)
                gara_soup = BeautifulSoup(r_gara.text, 'html.parser')
                
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
                    print("   ⚠️ Nessun atleta trovato con il formato atteso.")
                
                time.sleep(1) 
                
            except Exception as e:
                print(f"   ❌ Errore sulla gara {id_gara_fis}: {e}")

    except Exception as e:
        print(f"❌ Errore generale nello scraper: {e}")

if __name__ == "__main__":
    scraper_fis_master()
