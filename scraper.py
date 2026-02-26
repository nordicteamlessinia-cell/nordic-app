import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client

# Carica i segreti da GitHub
url_sb = os.environ.get("SUPABASE_URL")
key_sb = os.environ.get("SUPABASE_KEY")
supabase = create_client(url_sb, key_sb)

def scarica_test():
    # USIAMO L'ID REALE DI BOSCO CHIESANUOVA
    comp_id = "56789" 
    url = f"https://comitati.fisi.org/veneto/competizione/?idComp={comp_id}&d="
    
    print(f"--- Tentativo su Bosco Chiesanuova (ID: {comp_id}) ---")
    res = requests.get(url)
    soup = BeautifulSoup(res.text, 'html.parser')

    # Trova i link 'idGara=' (le classifiche effettive)
    links = [l['href'] for l in soup.find_all('a', href=True) if 'idGara=' in l['href']]
    
    if not links:
        print("❌ ATTENZIONE: Nessuna classifica (idGara) trovata in questa pagina!")
        return

    for g_url in list(set(links)):
        print(f"Scarico dettagli gara: {g_url}")
        res_g = requests.get(g_url)
        g_soup = BeautifulSoup(res_g.text, 'html.parser')
        
        # Cerca la tabella risultati
        table = g_soup.find('table')
        if table:
            rows = table.find_all('tr')[1:] # Salta intestazione
            batch = []
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 5:
                    batch.append({
                        "atleta_nome": cols[2].text.strip(),
                        "societa": cols[4].text.strip(),
                        "posizione": int(cols[0].text.strip()) if cols[0].text.strip().isdigit() else 0,
                        "id_gara_fisi": g_url.split('idGara=')[1].split('&')[0]
                    })
            
            if batch:
                supabase.table("gare").upsert(batch).execute()
                print(f"✅ SUCCESSO: Inseriti {len(batch)} atleti su Supabase!")

if __name__ == "__main__":
    scarica_test()
