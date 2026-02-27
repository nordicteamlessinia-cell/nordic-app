import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client

# 1. Configurazione Supabase
url_sb = os.environ.get("SUPABASE_URL")
key_sb = os.environ.get("SUPABASE_KEY")
supabase = create_client(url_sb, key_sb)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest'
}

def avvia_scraper_completo():
    comp_id = "56789"
    url_comp = f"https://comitati.fisi.org/veneto/competizione/?idComp={comp_id}&d="
    
    print(f"--- 🎯 FASE 1: Recupero elenco gare da {url_comp} ---")
    
    try:
        res = requests.get(url_comp, headers=HEADERS, timeout=30)
        soup = BeautifulSoup(res.text, 'html.parser')
        links = list(set([l['href'] for l in soup.find_all('a', href=True) if 'idGara=' in l['href']]))
        print(f"--- 📊 Gare identificate: {len(links)} ---")

        for g_url in links:
            id_gara = g_url.split('idGara=')[1].split('&')[0]
            print(f"\n--- 🔍 FASE 2: Analisi Gara {id_gara} ---")
            
            # Proviamo a scaricare la classifica
            url_dati = f"https://comitati.fisi.org/veneto/wp-admin/admin-ajax.php?action=get_classifica&idGara={id_gara}"
            res_dati = requests.get(url_dati, headers=HEADERS, timeout=30)
            
            # DEBUG: Vediamo se la risposta contiene effettivamente qualcosa
            html_content = res_dati.text.strip()
            if not html_content or html_content == "0":
                print(f"   ⚠️ Il server ha risposto vuoto (0) per la gara {id_gara}")
                continue

            data_soup = BeautifulSoup(html_content, 'html.parser')
            rows = data_soup.find_all(['tr', 'div']) # Cerchiamo sia righe che div
            atleti_batch = []
            
            for row in rows:
                cols = row.find_all(['td', 'span', 'div'], recursive=False)
                if not cols:
                    cols = row.find_all(True, recursive=False) # Prendi tutto se non trovi tag specifici
                
                data = [c.get_text(strip=True) for c in cols]
                
                # Cerchiamo una riga che abbia un numero (posizione) seguito da almeno altri 3 dati
                if len(data) >= 4:
                    # Troviamo la posizione (il primo numero nella lista)
                    pos = next((s for s in data if s.isdigit()), None)
                    if pos:
                        idx = data.index(pos)
                        # Di solito: Posizione=idx, Nome=idx+2, Società=idx+4
                        try:
                            nome = data[idx+2] if len(data) > idx+2 else "N.D."
                            soc = data[idx+4] if len(data) > idx+4 else "N.D."
                            
                            if len(nome) > 3: # Evitiamo righe di test corte
                                atleti_batch.append({
                                    "id_gara_fisi": id_gara,
                                    "posizione": int(pos),
                                    "atleta_nome": nome,
                                    "societa": soc
                                })
                        except:
                            continue

            if atleti_batch:
                print(f"   ✅ SUCCESSO: Trovati {len(atleti_batch)} atleti. Invio a Supabase...")
                supabase.table("Gare").upsert(atleti_batch).execute()
            else:
                print(f"   ❌ Impossibile interpretare i dati della gara {id_gara}. Contenuto: {html_content[:100]}...")

        print("\n--- 🏁 OPERAZIONE COMPLETATA ---")

    except Exception as e:
        print(f"--- 🔥 ERRORE GENERALE: {e} ---")

if __name__ == "__main__":
    avvia_scraper_completo()
