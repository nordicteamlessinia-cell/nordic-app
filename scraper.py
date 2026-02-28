import requests
from bs4 import BeautifulSoup

def indagine_blocco():
    id_comp = "56782" # La competizione che sappiamo avere gare
    url_comp = f"https://comitati.fisi.org/veneto/competizione/?idComp={id_comp}&d=2025"
    
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7'
    }

    print(f"--- 🎯 TEST CONNESSIONE: {url_comp} ---")
    
    try:
        res = requests.get(url_comp, headers=HEADERS, timeout=15)
        print(f"📡 Status Code: {res.status_code} (Se è 403, ci hanno bloccato)")
        
        soup = BeautifulSoup(res.text, 'html.parser')
        links = soup.find_all('a', href=True)
        
        id_sottogare = list(set([l['href'] for l in links if 'idGara=' in l['href']]))
        
        if id_sottogare:
            print(f"✅ FUNZIONA! Trovate {len(id_sottogare)} sottogare:")
            for s in id_sottogare:
                print(f"   🔗 {s}")
        else:
            print("❌ NESSUNA SOTTOGARA. Ecco cosa vede in realtà lo scraper (Primi 500 caratteri dell'HTML):")
            print("-" * 50)
            print(res.text[:500])
            print("-" * 50)
            
            # Verifichiamo se c'è Cloudflare
            if "Cloudflare" in res.text or "Just a moment" in res.text:
                print("⚠️ ALLARME ROSSO: Il server ci ha bloccato con un sistema Anti-Bot (Cloudflare).")

    except Exception as e:
        print(f"🔥 ERRORE DI CONNESSIONE: {e}")

if __name__ == "__main__":
    indagine_blocco()
