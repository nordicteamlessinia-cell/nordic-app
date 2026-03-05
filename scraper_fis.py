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

# Costanti e URL
BASE_URL = "https://www.fis-ski.com"
URL_CALENDARIO = f"{BASE_URL}/DB/cross-country/calendar-results.html?sectorcode=CC&nationcode=ita&seasonselection=2026"

# Mascheriamo il bot
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, come Gecko) Chrome/122.0.0.0 Safari/537.36'
}

def scraper_fis_master():
    print("--- 🌍 AVVIO SCRAPER FIS (ITALIA - 2026) ---")
    
    try:
        # FASE 1: Trovo tutti i link delle gare
        print("🔍 Cerco le gare nel calendario...")
        res = requests.get(URL_CALENDARIO, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        link_gare = []
        for a in soup.find_all('a', href=True):
           if 'results.html' in a.get('href', '') and 'raceid=' in a.get('href', ''):
                link_gare.append(a['href'])
                
        link_gare = list(set(link_gare)) # Rimuovo i duplicati
        print(f"🎯 Trovate {len(link_gare)} gare FIS in Italia. Inizio l'estrazione...\n")

        # FASE 2: Entro in ogni singola gara
        for link in link_gare:
            url_gara = BASE_URL + link
            id_gara_fis = link.split('raceid=')[1].split('&')[0] if 'raceid=' in link else "N/D"
            
            print(f"⛷️ Analizzo gara FIS ID: {id_gara_fis}")
            
            try:
                r_gara = requests.get(url_gara, headers=HEADERS, timeout=15)
                gara_soup = BeautifulSoup(r_gara.text, 'html.parser')
                
                # Cerco il titolo/categoria della gara in alto
                titolo_gara = gara_soup.find('h1').text.strip() if gara_soup.find('h1') else "Gara FIS"
                
                # La FIS usa spesso dei div o link specifici (classe g-row o pr-1) per gli atleti
                righe_atleti = gara_soup.find_all('div', class_='g-row')
                if not righe_atleti:
                    righe_atleti = gara_soup.find_all('a', class_='pr-1')
                
                batch_risultati = []
                
                for riga in righe_atleti:
                    # Estraggo tutti i testi puliti da questa riga
                    testi = [t.strip() for t in riga.stripped_strings if t.strip()]
                    
                    # Se ci sono abbastanza dati (es. Posizione, Codice, Nome, Anno, Nazione, Tempo, Punti)
                    if len(testi) >= 5:
                        try:
                            # Cerco il codice FIS (di solito è l'unico numero lungo a 6-7 cifre)
                            codice_fis = next((t for t in testi if len(t) >= 6 and t.isdigit()), "N/D")
                            
                            # Il tempo di solito contiene i due punti ":"
                            tempo = next((t for t in testi if ":" in t), "N/D")
                            
                            # I punti FIS spesso contengono un punto "."
                            punti_str = next((t for t in reversed(testi) if "." in t and t.replace('.','',1).isdigit()), "0.00")
                            
                            # Il Nome (il testo in maiuscolo/lungo che non è una sigla o numero)
                            nome = "N/D"
                            for t in testi:
                                if not t.isdigit() and ":" not in t and "." not in t and len(t) > 4 and t != "ITA":
                                    nome = t
                                    break
                                    
                            # Nazione
                            nazione = "ITA" if "ITA" in testi else "N/D"
                            
                            # Posizione (primo elemento se è un numero)
                            posizione_pulita = int(testi[0]) if testi[0].isdigit() else None
                            punti_puliti = float(punti_str) if punti_str != "0.00" else None

                            batch_risultati.append({
                                "id_gara_fis": id_gara_fis,
                                "data_gara": "2026", # Per ora assegniamo l'anno della query
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
                            continue # Se una riga fallisce, passo alla successiva senza bloccare tutto
                
                # FASE 3: Salvo su Supabase
                if batch_risultati:
                    supabase.table("Risultati_FIS").upsert(batch_risultati).execute()
                    print(f"   ✅ Salvati {len(batch_risultati)} atleti nel database!")
                else:
                    print("   ⚠️ Nessun atleta trovato con il formato atteso. (Hanno cambiato l'HTML della gara)")
                
                time.sleep(1) # Pausa vitale di 1 secondo per non farsi bannare
                
            except Exception as e:
                print(f"   ❌ Errore sulla gara {id_gara_fis}: {e}")

    except Exception as e:
        print(f"❌ Errore generale nello scraper: {e}")

if __name__ == "__main__":
    scraper_fis_master()
