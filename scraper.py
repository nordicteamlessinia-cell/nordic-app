import requests
from bs4 import BeautifulSoup

def test_cecchino_html():
    id_comp = "56782"
    id_g = "16299418" # La gara che hai linkato e che sappiamo essere piena!
    
    url_gara = f"https://comitati.fisi.org/veneto/gara/?idGara={id_g}&idComp={id_comp}&d=2025"
    HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'}
    
    print(f"--- 🎯 LETTURA DIRETTA HTML SULLA GARA: {id_g} ---")
    
    try:
        res = requests.get(url_gara, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 1. Cerchiamo le tabelle nella pagina
        tables = soup.find_all('table')
        
        if not tables:
            print("❌ Nessuna tabella HTML trovata nella pagina.")
            
            # 2. Se non c'è la tabella, cerchiamo un PDF!
            pdfs = [a['href'] for a in soup.find_all('a', href=True) if '.pdf' in a['href'].lower()]
            if pdfs:
                print(f"📄 MA HO TROVATO {len(pdfs)} FILE PDF! La FISI ha caricato la classifica come documento:")
                for p in pdfs:
                    print(f"   -> {p}")
            else:
                print("📝 Nessun PDF. Ecco cosa legge il bot nella pagina (Primi 500 caratteri):")
                print(soup.get_text(separator=' | ', strip=True)[:500])
            return

        print(f"✅ Trovate {len(tables)} tabelle HTML! Analisi in corso...")
        
        for table in tables:
            rows = table.find_all('tr')
            batch = []
            
            for row in rows:
                cols = row.find_all(['td', 'th'])
                if len(cols) >= 5:
                    d = [c.get_text(strip=True) for c in cols]
                    if d[0].isdigit(): # Se è una posizione numerica
                        batch.append(d)
            
            if batch:
                print(f"\n   🎉 VITTORIA! Estratti {len(batch)} atleti dalla tabella. Ecco i primi 3:")
                for b in batch[:3]:
                    print(f"      🥇 Pos: {b[0]} | Nome: {b[2]} | Società: {b[4]}")
                return
        
        print("⚠️ Tabelle trovate ma non contenevano atleti (struttura diversa).")

    except Exception as e:
        print(f"❌ Errore: {e}")

if __name__ == "__main__":
    test_cecchino_html()
