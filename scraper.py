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

# Header per non farsi bloccare dal sito
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def avvia_scarico():
    # ID della competizione di esempio (puoi cambiarlo con quello reale)
    comp_id = "56789" 
    url_competizione = f"https://comitati.fisi.org/veneto/competizione/?idComp={comp_id}&d="
    
    print(f"--- ANALISI COMPETIZIONE: {url_competizione} ---")
    
    try:
        res = requests.get(url_competizione, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(res.text, 'html.parser')

        # Cerchiamo i link alle singole categorie (es. U14, U16)
        links = [l['href'] for l in soup.find_all('a', href=True) if 'idGara=' in l['href']]
        links = list(set(links)) # Rimuove doppioni
        
        print(f"--- GARE TROVATE: {len(links)} ---")

        if not links:
            print("❌ Nessun link gara trovato. L'ID potrebbe essere errato o la pagina è vuota.")
            return

        for g_url in links:
            full_url = g_url if g_url.startswith('http') else f"https://comitati.fisi.org/veneto/{g_url}"
            id_fisi = full_url.split('idGara=')[1].split('&')[0]
            
            print(f"\n--- ANALIZZO CATEGORIA: {full_url} ---")
            res_g = requests.get(full_url, headers=HEADERS, timeout=30)
            g_soup = BeautifulSoup(res_g.text, 'html.parser')
            
            # Cerca il titolo della categoria (es. Ragazzi U14)
            titolo = g_soup.find('h1').text.strip() if g_soup.find('h1') else "Gara Veneto"

            # Cerchiamo la tabella
            table = g_soup.find('table')
            if not table:
                print("   ❌ Tabella non trovata in questa pagina.")
                continue

            rows = table.find_all('tr')
            batch_atleti = []

            for row in rows:
                cols = row.find_all(['td', 'th'])
                data = [c.get_text(strip=True) for c in cols]
                
                # Se la riga è corta, la saltiamo
                if len(data) < 4:
                    continue

                # STAMPA DI DEBUG (per vedere nei log di GitHub cosa succede)
                print(f"   Riga letta: {data}")

                # LOGICA DI ESTRAZIONE:
                # 1. Cerchiamo la posizione (un numero nella prima o seconda colonna)
                pos = None
                for i in range(min(2, len(data))):
                    if data[i].isdigit():
                        pos = int(data[i])
                        idx_start = i
                        break
                
                # 2. Se abbiamo trovato la posizione, estraiamo Atleta e Società
                if pos is not None:
                    # Di solito l'atleta è 2 posizioni dopo la classifica, la società 4
                    # Ma facciamo un controllo di sicurezza sulla lunghezza
                    nome = data[idx_start + 2] if len(data) > idx_start + 2 else "N.D."
                    soc = data[idx_start + 4] if len(data) > idx_start + 4 else "N.D."
                    tempo = data[idx_start + 5] if len(data) > idx_start + 5 else ""

                    batch_atleti.append({
                        "atleta_nome": nome,
                        "societa": soc,
                        "posizione": pos,
                        "tempo": tempo,
                        "categoria": titolo,
                        "id_gara_fisi": id_fisi,
                        "comp_id": comp_id
                    })

            if batch_atleti:
                print(f"   ✅ Trovati {len(batch_atleti)} atleti. Invio a Supabase...")
                # L'upsert evita duplicati se la tabella ha un indice univoco
                supabase.table("gare").upsert(batch_atleti).execute()
            else:
                print("   ⚠ Nessun atleta valido estratto da questa tabella.")

    except Exception as e:
        print(f"❌ ERRORE CRITICO: {e}")

if __name__ == "__main__":
    avvia_scarico()
