import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client

# 1. Configurazione Credenziali
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Mancano le chiavi API nei Secrets di GitHub!")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Header per simulare un browser reale
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def avvia_scarico():
    # ID della competizione reale (Bosco Chiesanuova)
    comp_id = "56789" 
    url_competizione = f"https://comitati.fisi.org/veneto/competizione/?idComp={comp_id}&d="
    
    print(f"--- ANALISI COMPETIZIONE: {url_competizione} ---")
    
    try:
        res = requests.get(url_competizione, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(res.text, 'html.parser')

        # Cerchiamo i link alle singole classifiche
        links = [l['href'] for l in soup.find_all('a', href=True) if 'idGara=' in l['href']]
        links = list(set(links)) 
        
        print(f"--- GARE TROVATE: {len(links)} ---")

        for g_url in links:
            full_url = g_url if g_url.startswith('http') else f"https://comitati.fisi.org/veneto/{g_url}"
            id_fisi = full_url.split('idGara=')[1].split('&')[0]
            
            print(f"\n--- ANALIZZO CATEGORIA: {full_url} ---")
            res_g = requests.get(full_url, headers=HEADERS, timeout=30)
            g_soup = BeautifulSoup(res_g.text, 'html.parser')
            
            # Recupero il titolo della gara (h1 o titolo pagina)
            titolo = g_soup.find('h1').text.strip() if g_soup.find('h1') else "Gara Veneto"

            # 2. RICERCA AGGRESSIVA: Troviamo tutte le righe <tr> ovunque siano
            rows = g_soup.find_all('tr')
            
            if not rows:
                print("   ❌ Nessuna riga (tr) trovata. Controllo se i dati sono in div...")
                # Prova alternativa se il sito usa div invece di tabelle
                rows = g_soup.find_all('div', class_='row')

            batch_atleti = []

            for row in rows:
                # Estraiamo tutto il testo dalle celle (td o div)
                cols = row.find_all(['td', 'div', 'th'])
                data = [c.get_text(strip=True) for c in cols]
                
                if len(data) < 4:
                    continue

                # Identifichiamo la posizione (primo numero trovato nella riga)
                pos = None
                idx_pos = -1
                for i, val in enumerate(data):
                    if val.isdigit():
                        pos = int(val)
                        idx_pos = i
                        break
                
                # Se abbiamo una posizione, estraiamo i dati relativi
                if pos is not None and len(data) > idx_pos + 4:
                    print(f"   Dati estratti: {data}")
                    batch_atleti.append({
                        "atleta_nome": data[idx_pos + 2],
                        "societa": data[idx_pos + 4],
                        "posizione": pos,
                        "tempo": data[idx_pos + 5] if len(data) > idx_pos + 5 else "",
                        "categoria": titolo,
                        "id_gara_fisi": id_fisi,
                        "comp_id": comp_id
                    })

            if batch_atleti:
                print(f"   ✅ Trovati {len(batch_atleti)} atleti. Invio a Supabase...")
                supabase.table("gare").upsert(batch_atleti).execute()
            else:
                print("   ⚠ Nessun atleta trovato in questa pagina.")

    except Exception as e:
        print(f"❌ ERRORE: {e}")

if __name__ == "__main__":
    avvia_scarico()
