import requests
from bs4 import BeautifulSoup

def test_estrazione_custom():
    url_gara = "https://comitati.fisi.org/veneto/gara/?idGara=16285788&idComp=54572&d="
    HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'}
    
    print("--- 🎯 ESTRAZIONE ATLETI DAL LAYOUT SEGRETO ---")
    
    try:
        res = requests.get(url_gara, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 👉 LA CHIAVE MAGICA: Cerchiamo la classe che hai trovato tu!
        elementi_atleti = soup.find_all('span', class_='x-text-content-text-primary')
        
        nomi_puliti = []
        for elemento in elementi_atleti:
            testo = elemento.get_text(strip=True)
            # Filtriamo via testi troppo corti o vuoti per tenere solo i nomi veri
            if len(testo) > 3:
                nomi_puliti.append(testo)
                
        if nomi_puliti:
            print(f"✅ VITTORIA ASSOLUTA! Estratti {len(nomi_puliti)} nomi.")
            print("\nEcco i primi 10 sciatori trovati:")
            for i, nome in enumerate(nomi_puliti[:10], start=1):
                print(f"   {i}. ⛷️ {nome}")
        else:
            print("❌ Nessun nome trovato.")

    except Exception as e:
        print(f"❌ Errore: {e}")

if __name__ == "__main__":
    test_estrazione_custom()
