import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client

# 1. Recupero credenziali dai Secrets di GitHub
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

# Inizializzazione client Supabase
if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Errore: SUPABASE_URL o SUPABASE_KEY non trovati nei Secrets di GitHub")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Header per simulare un browser ed evitare blocchi
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def avvia_scarico():
    # ID della competizione (Campionati Regionali Bosco Chiesanuova)
    comp_id = "56789" 
    url_competizione = f"https://comitati.fisi.org/veneto/competizione/?idComp={comp_id}&d="
    
    print(f"--- 1. Analizzo la competizione: {url_competizione} ---")
    
    try:
        res = requests.get(url_competizione, headers=HEADERS, timeout=20)
        soup = BeautifulSoup(res.text, 'html.parser')

        # Cerchiamo i link alle singole classifiche
        links = [l['href'] for l in soup.find_all('a', href=True) if 'idGara=' in l['href']]
        links = list(set(links))
        
        print(f"--- 2. Gare trovate: {len(links)} ---")

        for g_url in links:
            full_url = g_url if g_url.startswith('http') else f"https://comitati.fisi.org/veneto/{g_url}"
            id_fisi = full_url.split('idGara=')[1].split('&')[0]
            
            print(f"--- 3. Analizzo dettagli gara: {full_url} ---")
            res_g = requests.get(full_url, headers=HEADERS, timeout=20)
            g_soup = BeautifulSoup(res_g.text, 'html.parser')
            
            titolo_gara = g_soup.find('h1').text.strip() if g_soup.find('h1') else "Gara Veneto"
            rows = g_soup.find_all('tr')
            batch_atleti = []

            for row in rows:
                cols = row.find_all(['td', 'th'])
                data = [c.get_text(strip=True) for c in cols]
                
                if len(data) > 3:
                    # Log per debug: vediamo la struttura nel log di GitHub
                    print(f"   Dati riga: {data}")

                    # Cerchiamo la posizione nelle prime due colonne
                    pos = None
                    for potential_pos in data[:2]:
                        if potential_pos.isdigit():
                            pos = int(potential_pos)
                            break
                    
                    # Se troviamo la posizione e i dati minimi, aggiungiamo al batch
                    if pos is not None and len(data) >= 5:
                        batch_atleti.append({
                            "atleta_nome": data[2],
                            "societa": data[4],
                            "posizione": pos,
                            "tempo": data[5] if len(data) > 5 else "",
                            "categoria": titolo_gara,
                            "id_gara_fisi": id_fisi,
                            "comp_id": comp_id
                        })

            if batch_atleti:
                print(f"   ✅ Invio {len(batch_atleti)} atleti a Supabase...")
                supabase.table("gare").upsert(batch_atleti).execute()
            else:
                print("   ⚠ Nessun dato estratto da questa tabella.")

    except Exception as e:
        print(f"❌ ERRORE GENERALE: {e}")

if __name__ == "__main__":
    avvia_scarico()
