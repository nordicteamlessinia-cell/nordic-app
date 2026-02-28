import requests
from bs4 import BeautifulSoup
import re

def indagine_raggi_x():
    url_test = "https://comitati.fisi.org/veneto/gara/?idGara=16284864&idComp=54457&d=2025"
    HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'}

    print(f"--- 🔦 INDAGINE PROFONDA SULLA GARA 16284864 ---")
    res = requests.get(url_test, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(res.text, 'html.parser')

    # 1. Cerchiamo file PDF
    pdf_links = [a['href'] for a in soup.find_all('a', href=True) if '.pdf' in a['href'].lower()]
    if pdf_links:
        print(f"\n📄 TROVATI {len(pdf_links)} PDF! Le classifiche sono documenti:")
        for p in pdf_links:
            print(f"   -> {p}")

    # 2. Cerchiamo chiamate AJAX nascoste nel JavaScript
    scripts = soup.find_all('script')
    trovato_ajax = False
    for script in scripts:
        if script.string and ('admin-ajax.php' in script.string or 'action' in script.string):
            # Cerchiamo l'azione esatta
            action = re.search(r"action\s*:\s*['\"]([^'\"]+)['\"]", script.string)
            if action:
                print(f"\n🕵️‍♂️ TROVATO SCRIPT AJAX NASCOSTO!")
                print(f"   🎯 LA VERA AZIONE API È: {action.group(1)}")
                trovato_ajax = True

    # 3. Cerchiamo strutture alternative (se non è né PDF né AJAX)
    if not pdf_links and not trovato_ajax:
        print("\n👽 STRUTTURA HTML ALTERNATIVA TROVATA. Ricerca blocchi dati...")
        # Estraiamo tutto il testo pulito per vedere se i nomi ci sono
        testo = soup.get_text(separator=' | ', strip=True)
        print(f"   📝 Anteprima testo: {testo[:500]}...")

if __name__ == "__main__":
    indagine_raggi_x()
