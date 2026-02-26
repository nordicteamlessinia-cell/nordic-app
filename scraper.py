import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client

# Configurazione
url_supabase = os.environ.get("SUPABASE_URL")
key_supabase = os.environ.get("SUPABASE_KEY")
supabase = create_client(url_supabase, key_supabase)

def scarica_classifiche():
    comp_id = "56789"
    url_competizione = f"https://comitati.fisi.org/veneto/competizione/?idComp={comp_id}&d="
    
    print(f"--- Inizio analisi competizione {comp_id} ---")
    res = requests.get(url_competizione)
    soup = BeautifulSoup(res.text, 'html.parser')

    # Cerchiamo tutti i link alle singole gare
    links = soup.find_all('a', href=True)
    gare = [l['href'] for l in links if 'idGara=' in l['href']]
    
    # Rimuoviamo i duplicati
    gare = list(set(gare))
    print(f"Trovate {len(gare)} gare da analizzare.")

    for g_url in gare:
        id_gara = g_url.split('idGara=')[1].split('&')[0]
        print(f"Analizzo gara ID {id_gara}...")
        
        res_g = requests.get(g_url)
        g_soup = BeautifulSoup(res_g.text, 'html.parser')
        
        # Cerchiamo la tabella (nel sito FISI è solitamente l'unica table)
        table = g_soup.find('table')
        if not table:
            print(f"Nessuna tabella trovata per la gara {id_gara}")
            continue

        rows = table.find_all('tr')
        dati_da_inserire = []

        for row in rows[1:]: # Salta l'intestazione
            cols = row.find_all('td')
            # La tabella FISI ha: Pos | Pett | Atleta | Anno | Società | Tempo
            if len(cols) >= 5:
                pos = cols[0].text.strip()
                atleta = cols[2].text.strip()
                societa = cols[4].text.strip()
                tempo = cols[5].text.strip() if len(cols) > 5 else ""

                # Solo se la posizione è un numero (evita righe di testo extra)
                if pos.isdigit():
                    dati_da_inserire.append({
                        "id_gara_fisi": id_gara,
                        "Atleta": Atleta,
                        "societa": societa,
                        "posizione": int(pos),
                        "tempo": tempo,
                        "gara_id": comp_id
                    })

        if dati_da_inserire:
            # Upsert evita duplicati se lanci lo script più volte
            supabase.table("gare").upsert(dati_da_inserire, on_conflict="id_gara_fisi, atleta_nome").execute()
            print(f"Inseriti {len(dati_da_inserire)} atleti per la gara {id_gara}")

if __name__ == "__main__":
    scarica_classifiche()
