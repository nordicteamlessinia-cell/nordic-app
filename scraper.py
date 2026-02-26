import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client

# Configurazione Supabase
url_sb = os.environ.get("SUPABASE_URL")
key_sb = os.environ.get("SUPABASE_KEY")
supabase = create_client(url_sb, key_sb)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/110.0.0.0 Safari/537.36'}

def avvia():
    comp_id = "56789" 
    url_competizione = f"https://comitati.fisi.org/veneto/competizione/?idComp={comp_id}&d="
    
    print(f"--- 1. ANALIZZO COMPETIZIONE: {url_competizione} ---")
    res = requests.get(url_competizione, headers=HEADERS)
    soup = BeautifulSoup(res.text, 'html.parser')

    # 2. Trova i link delle gare
    links = [l['href'] for l in soup.find_all('a', href=True) if 'idGara=' in l['href']]
    
    for g_url in list(set(links)):
        full_url = g_url if g_url.startswith('http') else f"https://comitati.fisi.org/veneto/{g_url}"
        print(f"--- 2. ENTRO NELLA GARA: {full_url} ---")
        
        res_g = requests.get(full_url, headers=HEADERS)
        g_soup = BeautifulSoup(res_g.text, 'html.parser')
        
        # 3. CERCA L'IFRAME (Il vero contenitore dei dati)
        iframe = g_soup.find('iframe')
        if iframe and 'src' in iframe.attrs:
            real_data_url = iframe['src']
            print(f"--- 3. TROVATA FINESTRA DATI: {real_data_url} ---")
            
            # Saltiamo dentro l'Iframe per leggere la tabella
            res_data = requests.get(real_data_url, headers=HEADERS)
            data_soup = BeautifulSoup(res_data.text, 'html.parser')
            
            table = data_soup.find('table')
            if table:
                rows = table.find_all('tr')[1:] # Salta intestazione
                atleti = []
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 5:
                        atleti.append({
                            "atleta_nome": cols[2].text.strip(),
                            "societa": cols[4].text.strip(),
                            "posizione": int(cols[0].text.strip()) if cols[0].text.strip().isdigit() else 0,
                            "id_gara_fisi": full_url.split('idGara=')[1].split('&')[0]
                        })
                
                if atleti:
                    print(f"--- 4. ✅ SUCCESSO: Trovati {len(atleti)} atleti. Invio a Supabase... ---")
                    supabase.table("gare").upsert(atleti).execute()
            else:
                print("--- 4. ❌ Tabella non trovata neanche nell'Iframe. ---")
        else:
            print("--- 3. ❌ Nessun Iframe trovato in questa pagina. ---")

if __name__ == "__main__":
    avvia()
