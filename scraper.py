import requests
from bs4 import BeautifulSoup

def ispeziona_intestazione():
    # Usiamo la nostra "Gara Dorata" di test
    url_gara = "https://comitati.fisi.org/veneto/gara/?idGara=16285788&idComp=54572&d=2026"
    HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    print("--- 🔍 ISPEZIONE INTESTAZIONE GARA ---")
    try:
        res = requests.get(url_gara, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        elementi = soup.find_all('span', class_='x-text-content-text-primary')
        testi = [e.get_text(strip=True) for e in elementi if len(e.get_text(strip=True)) > 0]
        
        print("Ecco le prime 30 'scatole' della pagina:\n")
        for i, t in enumerate(testi[:30]):
            print(f"   [{i}] {t}")
            
    except Exception as e:
        print(f"❌ Errore: {e}")

if __name__ == "__main__":
    ispeziona_intestazione()
