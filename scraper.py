import os
import requests
from bs4 import BeautifulSoup

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
}

def cerca_documenti_nascosti():
    # Torniamo alla pagina principale della competizione
    comp_id = "56789" 
    url_principale = f"https://comitati.fisi.org/veneto/competizione/?idComp={comp_id}&d="
    
    print(f"--- RICERCA DOCUMENTI SU: {url_principale} ---")
    
    try:
        res = requests.get(url_principale, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # Cerchiamo tutti i link che contengono file scaricabili
        links = soup.find_all('a', href=True)
        
        print(f"--- Analisi di {len(links)} link totali ---")
        
        documenti_trovati = 0
        for l in links:
            href = l['href']
            testo = l.get_text(strip=True).upper()
            
            # Cerchiamo estensioni di file o parole chiave nel testo del link
            estensioni = ['.pdf', '.xlsx', '.xls', '.doc', '.zip']
            if any(ext in href.lower() for ext in estensioni) or "CLASSIFICA" in testo:
                full_url = href if href.startswith('http') else f"https://comitati.fisi.org/veneto/{href}"
                print(f"📄 DOCUMENTO TROVATO: {testo} -> {full_url}")
                documenti_trovati += 1
        
        if documenti_trovati == 0:
            print("❌ Nessun file trovato. I risultati potrebbero essere caricati via JavaScript o non ancora pubblicati.")
            
    except Exception as e:
        print(f"❌ Errore: {e}")

if __name__ == "__main__":
    cerca_documenti_nascosti()
