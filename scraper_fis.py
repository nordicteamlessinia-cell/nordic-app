import requests
from bs4 import BeautifulSoup
import time

def estrai_classifica_veloce(raceid):
    url = f"https://www.fis-ski.com/DB/general/results.html?sectorcode=CC&raceid={raceid}"
    
    # Headers finti per non farsi bloccare come bot
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    }

    print(f"🚀 Scarico i dati della gara {raceid} in modalità ultra-veloce...")
    
    start_time = time.time()
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Errore di connessione: {response.status_code}")
        return

    # Usiamo BeautifulSoup per analizzare l'HTML che è già "cotto" dal server
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Cerchiamo tutte le righe della tabella (la FIS usa il tag 'a' con classe 'table-row')
    righe_atleti = soup.find_all("a", class_="table-row")
    
    print(f"✅ Pagina scaricata in {round(time.time() - start_time, 2)} secondi!")
    print(f"🎯 Trovati {len(righe_atleti)} atleti in classifica.\n")
    print("-" * 50)

    risultati = []

    for riga in righe_atleti:
        try:
            # Estraiamo i dati usando i selettori CSS (molto più stabili)
            nome_tag = riga.find("div", class_="athlete-name")
            nazione_tag = riga.find("span", class_="country__name-short")
            
            # PuliAMO i testi da spazi extra e ritorni a capo
            nome = nome_tag.text.strip() if nome_tag else "N/D"
            nazione = nazione_tag.text.strip() if nazione_tag else "N/D"
            
            # Sulla FIS, i div dentro la riga seguono un ordine preciso.
            # Estraiamo tutti i testi delle colonne per non sbagliare.
            colonne = [col.text.strip() for col in riga.find_all("div") if col.text.strip()]
            
            # Solitamente la posizione è il primo elemento o il secondo
            posizione = colonne[0] if colonne else "N/D"
            
            print(f"⛷️ Pos: {posizione} | Atleta: {nome} ({nazione})")
            
            risultati.append({
                "posizione": posizione,
                "nome": nome,
                "nazione": nazione
            })
            
        except Exception as e:
            continue
            
    print("-" * 50)
    print("🏆 Estrazione completata con successo, pronta per Supabase!")

if __name__ == "__main__":
    estrai_classifica_veloce(50468)
