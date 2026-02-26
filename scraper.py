import os
import requests
from bs4 import BeautifulSoup

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}

def caccia_link():
    url_gara = "https://comitati.fisi.org/veneto/gara/?idGara=16299551&idComp=56789&d="
    print(f"--- ANALISI LINK SOSPETTI SU: {url_gara} ---")
    
    res = requests.get(url_gara, headers=HEADERS)
    soup = BeautifulSoup(res.text, 'html.parser')
    links = soup.find_all('a', href=True)

    print(f"--- Trovati {len(links)} link totali. Ecco quelli interessanti: ---")
    
    parole_chiave = ['classifica', 'pdf', 'fisi', 'download', 'risultati', 'file']
    
    for l in links:
        href = l['href']
        testo = l.get_text().lower()
        # Se il link contiene una parola chiave o finisce con estensioni file
        if any(p in href.lower() or p in testo for p in parole_chiave):
            full_url = href if href.startswith('http') else f"https://comitati.fisi.org/veneto/{href}"
            print(f"🎯 TROVATO: {testo} -> {full_url}")

if __name__ == "__main__":
    caccia_link()
