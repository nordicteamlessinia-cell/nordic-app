import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client

# Carica le chiavi dalle impostazioni segrete di GitHub
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

def get_data():
    comp_id = "56789"
    url_fisi = f"https://comitati.fisi.org/veneto/competizione/?idComp={comp_id}&d="
    
    print(f"Collegamento a FISI Veneto per competizione {comp_id}...")
    resp = requests.get(url_fisi)
    soup = BeautifulSoup(resp.text, 'html.parser')
    
    # Cerchiamo i link alle gare
    links = soup.find_all('a', href=True)
    gare_trovate = [l['href'] for l in links if 'idGara=' in l['href']]
    
    for g_url in gare_trovate:
        id_gara = g_url.split('idGara=')[1].split('&')[0]
        print(f"Scarico gara {id_gara}...")
        
        # Qui lo script entra nella gara ed estrae la tabella
        res_g = requests.get(g_url)
        g_soup = BeautifulSoup(res_g.text, 'html.parser')
        rows = g_soup.find_all('tr')
        
        for row in rows[1:]:
            cols = row.find_all('td')
            if len(cols) >= 5:
                atleta = cols[2].text.strip()
                soc = cols[4].text.strip()
                pos = cols[0].text.strip()
                
                # Invio a Supabase
                supabase.table("gare").upsert({
                    "id_gara_fisi": id_gara,
                    "atleta_nome": atleta,
                    "societa": soc,
                    "posizione": int(pos) if pos.isdigit() else 0,
                    "gara_id": comp_id
                }).execute()

if __name__ == "__main__":
    get_data()
