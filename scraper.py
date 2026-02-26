import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client

# 1. Configurazione Iniziale
url_sb = os.environ.get("SUPABASE_URL")
key_sb = os.environ.get("SUPABASE_KEY")
supabase = create_client(url_sb, key_sb)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

def avvia_scarico_totale():
    # Usiamo l'ID della competizione che hai indicato
    comp_id = "56789" 
    url_fisi = f"https://comitati.fisi.org/veneto/competizione/?idComp={comp_id}&d="
    
    print(f"--- 1. Analizzo competizione: {url_fisi} ---")
    res = requests.get(url_fisi, headers=HEADERS)
    soup = BeautifulSoup(res.text, 'html.parser')

    # 2. Definizione della variabile 'links' (qui è dove prima c'era l'errore)
    links = [l['href'] for l in soup.find_all('a', href=True) if 'idGara=' in l['href']]
    links = list(set(links)) # Rimuove i doppioni
    
    print(f"--- 2. Gare trovate: {len(links)} ---")

    if not links:
        print("❌ Nessuna gara trovata nella pagina principale.")
        return

    for g_url in links:
        # Costruiamo l'URL completo
        full_url = g_url if g_url.startswith('http') else f"https://comitati.fisi.org/veneto/{g_url}"
        print(f"--- 3. Analizzo gara: {full_url} ---")
        
        try:
            res_g = requests.get(full_url, headers=HEADERS)
            g_soup = BeautifulSoup(res_g.text, 'html.parser')
            
            # Cerchiamo tutte le righe della tabella risultati
            rows = g_soup.find_all('tr')
            atleti = []

            for row in rows:
                cols = row.find_all(['td', 'th'])
                data = [c.get_text(strip=True) for c in cols]
                
                # Verifichiamo se la riga contiene dati validi (Posizione numerica)
                if len(data) >= 5 and data[0].isdigit():
                    atleti.append({
                        "atleta_nome": data[2],
                        "societa": data[4],
                        "posizione": int(data[0]),
                        "id_gara_fisi": full_url.split('idGara=')[1].split('&')[0],
                        "gara_nome": g_soup.find('h1').text.strip() if g_soup.find('h1') else "Gara Veneto"
                    })
            
            if atleti:
                print(f"   ✅ Trovati {len(atleti)} atleti. Invio a Supabase...")
                supabase.table("gare").upsert(atleti).execute()
            else:
                print("   ⚠ Nessun dato trovato nelle righe di questa gara.")

        except Exception as e:
            print(f"   🔥 Errore durante l'analisi della gara {full_url}: {e}")

if __name__ == "__main__":
    avvia_scarico_totale()
