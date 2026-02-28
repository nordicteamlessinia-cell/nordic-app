import requests
from bs4 import BeautifulSoup

def mappa_il_ritmo():
    url_gara = "https://comitati.fisi.org/veneto/gara/?idGara=16285788&idComp=54572&d="
    HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'}
    
    print("--- 🔍 CERCO IL RITMO ESATTO DEI DATI ---")
    
    try:
        res = requests.get(url_gara, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        elementi = soup.find_all('span', class_='x-text-content-text-primary')
        # Creiamo una lista pulita di tutti i testi
        testi = [e.get_text(strip=True) for e in elementi if len(e.get_text(strip=True)) > 0]
        
        # Troviamo a che numero della lista si trova il nostro Martino
        indice_martino = -1
        for i, t in enumerate(testi):
            if "MARTINO CAROLLO" in t.upper() or "CAROLLO MARTINO" in t.upper():
                indice_martino = i
                break
                
        if indice_martino != -1:
            print("✅ TROVATO! Ecco come sono disposti i dati in fila:\n")
            
            # Stampiamo 4 testi PRIMA del nome e 6 testi DOPO
            inizio = max(0, indice_martino - 4)
            fine = min(len(testi), indice_martino + 7)
            
            for i in range(inizio, fine):
                if i == indice_martino:
                    print(f" 🎯 [{i}] {testi[i]}  <-- IL NOME")
                else:
                    print(f"    [{i}] {testi[i]}")
                    
            print("\n💡 Incolla questo risultato, ci dirà esattamente come creare i blocchi per Supabase!")
        else:
            print("❌ Martino non trovato. Forse era scritto diversamente?")

    except Exception as e:
        print(f"❌ Errore: {e}")

if __name__ == "__main__":
    mappa_il_ritmo()
