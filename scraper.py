import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client
import re

# 1. Configurazione Supabase
url_sb = os.environ.get("SUPABASE_URL")
key_sb = os.environ.get("SUPABASE_KEY")
supabase = create_client(url_sb, key_sb)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
}

def avvia_scraper_definitivo():
    comp_id = "56789"
    url_comp = f"https://comitati.fisi.org/veneto/competizione/?idComp={comp_id}&d="
    
    print(f"--- 🎯 FASE 1: Recupero elenco gare ---")
    
    try:
        res = requests.get(url_comp, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(res.text, 'html.parser')
        links = list(set([l['href'] for l in soup.find_all('a', href=True) if 'idGara=' in l['href']]))
        print(f"--- 📊 Gare identificate: {len(links)} ---")

        for g_url in links:
            # Assicuriamoci che l'URL sia completo
            full_url = g_url if g_url.startswith('http') else f"https://comitati.fisi.org/veneto/{g_url}"
            id_gara = re.search(r'idGara=(\d+)', full_url).group(1)
            
            print(f"\n--- 🔍 FASE 2: Analisi Diretta Pagina Gara {id_gara} ---")
            
            # Leggiamo direttamente la pagina della gara
            res_g = requests.get(full_url, headers=HEADERS, timeout=30)
            g_soup = BeautifulSoup(res_g.text, 'html.parser')
            
            # Cerchiamo qualsiasi tabella presente nella pagina
            tables = g_soup.find_all('table')
            atleti_batch = []
            
            for table in tables:
                rows = table.find_all('tr')
                for row in rows:
                    cols = row.find_all(['td', 'th'])
                    data = [c.get_text(strip=True) for c in cols]
                    
                    # Logica: la riga deve avere la posizione (numero) nella prima colonna
                    if len(data) >= 5 and data[0].isdigit():
                        atleti_batch.append({
                            "id_gara_fisi": id_gara,
                            "posizione": int(data[0]),
                            "atleta_nome": data[2],
                            "societa": data[4]
                        })

            if atleti_batch:
                print(f"   ✅ TROVATI: {len(atleti_batch)} atleti. Invio a Supabase...")
                supabase.table("Gare").upsert(atleti_batch).execute()
            else:
                # Se non c'è tabella, cerchiamo il link al PDF come ultima spiaggia
                pdf_link = g_soup.find('a', href=re.compile(r'\.pdf'))
                if pdf_link:
                    print(f"   📄 Trovato PDF (Classifica non leggibile testualmente): {pdf_link['href']}")
                else:
                    print(f"   ❌ Nessun dato trovato nella pagina HTML per la gara {id_gara}")

        print("\n--- 🏁 PROCESSO FINITO ---")

    except Exception as e:
        print(f"--- 🔥 ERRORE: {e} ---")

if __name__ == "__main__":
    avvia_scraper_definitivo()
