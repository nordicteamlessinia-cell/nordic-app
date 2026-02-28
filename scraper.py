import requests
from bs4 import BeautifulSoup

def detective_invisibile():
    # La tua "Gara Dorata"
    url_gara = "https://comitati.fisi.org/veneto/gara/?idGara=16285788&idComp=54572&d="
    HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'}
    
    print(f"--- 🕵️‍♂️ CACCIA AI DATI NASCOSTI SULLA GARA: 16285788 ---")
    
    try:
        res = requests.get(url_gara, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 1. Cerchiamo IFRAME (Cornici che incorporano altre pagine)
        iframes = soup.find_all('iframe')
        if iframes:
            print(f"\n✅ VITTORIA! Trovati {len(iframes)} IFRAME. La classifica viene caricata da qui:")
            for iframe in iframes:
                print(f"   👉 SRC: {iframe.get('src')}")
            return # Se lo troviamo, ci fermiamo qui, abbiamo vinto.
        else:
            print("❌ Nessun Iframe trovato.")

        # 2. Cerchiamo SCRIPT o JSON nascosti
        print("\n🔍 Cerco JSON o dati nascosti nel codice...")
        scripts = soup.find_all('script')
        trovato_script = False
        for s in scripts:
            if s.string and ('classifica' in s.string.lower() or 'risultati' in s.string.lower()):
                print(f"   ⚠️ Sospetto Script JS trovato! Primi 200 caratteri:")
                print(f"   {s.string.strip()[:200]}")
                trovato_script = True
        
        if not trovato_script:
            print("❌ Nessun dato nascosto negli script.")

        # 3. Estraiamo link sospetti (forse c'è un bottone "Vai ai risultati" che non abbiamo visto)
        print("\n🔗 Link presenti nella pagina (Filtro per 'risultati' / 'fisionline'):")
        links = soup.find_all('a', href=True)
        for l in links:
            url = l['href'].lower()
            if 'risultat' in url or 'classific' in url or 'fisionline' in url or 'fisi.org' in url:
                print(f"   -> {l['href']}")

    except Exception as e:
        print(f"❌ Errore: {e}")

if __name__ == "__main__":
    detective_invisibile()
