import requests
from bs4 import BeautifulSoup

def test_gara_dorata():
    id_comp = "54572"
    id_g = "16285788"
    
    url_gara = f"https://comitati.fisi.org/veneto/gara/?idGara={id_g}&idComp={id_comp}&d="
    HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'}
    
    print(f"--- 🎯 ANALISI DELLA GARA DORATA: {id_g} ---")
    
    try:
        # TENTATIVO 1: Lettura diretta della pagina HTML
        res = requests.get(url_gara, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        tables = soup.find_all('table')
        if tables:
            print(f"✅ VITTORIA HTML! Trovate {len(tables)} tabelle direttamente nella pagina.")
            for table in tables:
                rows = table.find_all('tr')
                print("\n   Ecco le prime 3 righe trovate:")
                for row in rows[:3]: 
                    cols = row.find_all(['td', 'th'])
                    print("   " + " | ".join([c.get_text(strip=True) for c in cols]))
            return
            
        print("❌ Nessuna tabella visibile nell'HTML. Passo al livello 2...")
        
        # TENTATIVO 2: Ricerca di file PDF allegati
        pdfs = [a['href'] for a in soup.find_all('a', href=True) if '.pdf' in a['href'].lower()]
        if pdfs:
            print(f"📄 TROVATI {len(pdfs)} PDF ALLEGATI! Le classifiche sono documenti scaricabili:")
            for p in pdfs:
                print(f"   -> {p}")
            return
            
        print("❌ Nessun PDF trovato. Passo al livello 3 (API nascosta)...")
        
        # TENTATIVO 3: Chiamata AJAX al server
        BASE_URL = "https://comitati.fisi.org/wp-admin/admin-ajax.php"
        params = {"action": "get_classifica", "idGara": id_g}
        
        headers_ajax = HEADERS.copy()
        headers_ajax['Referer'] = url_gara
        headers_ajax['X-Requested-With'] = 'XMLHttpRequest'
        
        r_ajax = requests.get(BASE_URL, params=params, headers=headers_ajax, timeout=15)
        
        if r_ajax.text != "0" and len(r_ajax.text.strip()) > 100:
            print("✅ VITTORIA AJAX! I dati vengono caricati dinamicamente dal server.")
            soup_ajax = BeautifulSoup(r_ajax.text, 'html.parser')
            rows = soup_ajax.find_all('tr')
            print("\n   Ecco i primi atleti estratti dall'API:")
            for row in rows[:3]:
                cols = row.find_all(['td', 'th'])
                print("   " + " | ".join([c.get_text(strip=True) for c in cols]))
            return
            
        print("⚠️ Nessun dato trovato in nessuno dei 3 modi.")
        print("   Anteprima testo pagina:", soup.get_text(separator=' ', strip=True)[:200])

    except Exception as e:
        print(f"❌ Errore durante l'analisi: {e}")

if __name__ == "__main__":
    test_gara_dorata()
