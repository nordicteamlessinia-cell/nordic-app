import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client

# Collegamento Supabase
url_sb = os.environ.get("SUPABASE_URL")
key_sb = os.environ.get("SUPABASE_KEY")
supabase = create_client(url_sb, key_sb)

def ottieni_calendario_e_scarica():
    # Pagina principale del calendario Veneto
    url_calendario = "https://comitati.fisi.org/veneto/calendario/"
    res = requests.get(url_calendario)
    soup = BeautifulSoup(res.text, 'html.parser')

    # 1. Trova tutti i link alle competizioni (?idComp=...)
    links = soup.find_all('a', href=True)
    comp_ids = list(set([l['href'].split('idComp=')[1].split('&')[0] for l in links if 'idComp=' in l['href']]))
    
    print(f"Trovate {len(comp_ids)} competizioni in calendario. Inizio scarico totale...")

    for c_id in comp_ids:
        scarica_singola_competizione(c_id)

def scarica_singola_competizione(comp_id):
    url_comp = f"https://comitati.fisi.org/veneto/competizione/?idComp={comp_id}&d="
    res = requests.get(url_comp)
    soup = BeautifulSoup(res.text, 'html.parser')
    
    # Trova i link alle singole gare interne (U14, U16, ecc.)
    links = soup.find_all('a', href=True)
    gare_urls = list(set([l['href'] for l in links if 'idGara=' in l['href']]))

    for g_url in gare_urls:
        id_fisi = g_url.split('idGara=')[1].split('&')[0]
        res_g = requests.get(g_url)
        g_soup = BeautifulSoup(res_g.text, 'html.parser')
        
        table = g_soup.find('table')
        if not table: continue

        rows = table.find_all('tr')
        batch = []
        for row in rows[1:]:
            cols = row.find_all('td')
            if len(cols) >= 5:
                pos = cols[0].text.strip()
                if pos.isdigit():
                    batch.append({
                        "atleta_nome": cols[2].text.strip(),
                        "societa": cols[4].text.strip(),
                        "posizione": int(pos),
                        "tempo": cols[5].text.strip() if len(cols)>5 else "",
                        "id_gara_fisi": id_fisi,
                        "comp_id": comp_id
                    })
        
        if batch:
            # Upsert carica i nuovi e aggiorna i vecchi senza errori
            supabase.table("gare").upsert(batch, on_conflict="id_gara_fisi, atleta_nome").execute()
            print(f"Gara {id_fisi} (Comp {comp_id}): Caricati {len(batch)} atleti.")

if __name__ == "__main__":
    ottieni_calendario_e_scarica()
    scarica_classifiche()
