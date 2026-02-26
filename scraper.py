import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client

# Configurazione API
url_sb = os.environ.get("SUPABASE_URL")
key_sb = os.environ.get("SUPABASE_KEY")
supabase = create_client(url_sb, key_sb)

def scarica_tutto_veneto():
    url_calendario = "https://comitati.fisi.org/veneto/calendario/"
    print("--- Accesso al Calendario FISI Veneto ---")
    res = requests.get(url_calendario)
    soup = BeautifulSoup(res.text, 'html.parser')

    # 1. Trova tutti gli ID Competizione
    links = soup.find_all('a', href=True)
    comp_ids = list(set([l['href'].split('idComp=')[1].split('&')[0] for l in links if 'idComp=' in l['href']]))
    
    print(f"Trovate {len(comp_ids)} competizioni totali. Inizio estrazione...")

    for c_id in comp_ids:
        url_comp = f"https://comitati.fisi.org/veneto/competizione/?idComp={c_id}&d="
        res_c = requests.get(url_comp)
        soup_c = BeautifulSoup(res_c.text, 'html.parser')
        
        # Trova il nome generale della competizione (es. Campionati Regionali)
        nome_generale = soup_c.find('h1').text.strip() if soup_c.find('h1') else "Gara Veneto"

        # 2. Trova le singole gare (idGara)
        links_g = soup_c.find_all('a', href=True)
        gare_urls = list(set([l['href'] for l in links_g if 'idGara=' in l['href']]))

        for g_url in gare_urls:
            id_fisi = g_url.split('idGara=')[1].split('&')[0]
            res_g = requests.get(g_url)
            g_soup = BeautifulSoup(res_g.text, 'html.parser')
            
            # Categoria specifica (es. U12 Cuccioli)
            categoria = g_soup.find('h1').text.strip() if g_soup.find('h1') else nome_generale

            table = g_soup.find('table')
            if not table: continue

            rows = table.find_all('tr')
            batch_data = []

            for row in rows[1:]:
                cols = row.find_all('td')
                if len(cols) >= 5:
                    pos_text = cols[0].text.strip()
                    if pos_text.isdigit():
                        batch_data.append({
                            "atleta_nome": cols[2].text.strip(),
                            "societa": cols[4].text.strip(),
                            "posizione": int(pos_text),
                            "tempo": cols[5].text.strip() if len(cols) > 5 else "",
                            "categoria": categoria,
                            "gara_nome": nome_generale,
                            "id_gara_fisi": id_fisi,
                            "comp_id": c_id
                        })
            
            if batch_data:
                # Carichiamo i dati a blocchi (batch) per velocità
                supabase.table("gare").upsert(batch_data, on_conflict="id_gara_fisi, atleta_nome").execute()
                print(f"Salvati {len(batch_data)} atleti per: {categoria}")

if __name__ == "__main__":
    scarica_tutto_veneto()
