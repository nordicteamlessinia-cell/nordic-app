import os
import requests
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BASE_URL = "https://comitati.fisi.org/wp-admin/admin-ajax.php"

def scarica_risultati_atleti():
    print("--- 📚 RECUPERO GARE DA SUPABASE ---")
    gare_db = supabase.table("Gare").select("id_gara_fisi").execute()
    lista_id = [g['id_gara_fisi'] for g in gare_db.data]

    print(f"--- 🚀 ANALISI DI {len(lista_id)} GARE ---")

    for id_gara in lista_id[:10]: # Proviamo le prime 10 per test
        # L'azione corretta spesso richiede sia idGara che l'azione specifica
        params = {
            "action": "get_classifica", # Proviamo get_classifica che è più comune
            "idGara": id_gara 
        }
        
        try:
            r = requests.get(BASE_URL, params=params, timeout=15)
            
            # Se il server risponde "0", l'azione è sbagliata o la gara non ha ancora risultati
            if r.text == "0" or not r.text.strip():
                print(f"   ⚪ Gara {id_gara}: Nessun risultato disponibile o gara futura.")
                continue

            # Proviamo a leggere il JSON o l'HTML
            try:
                dati = r.json()
                # Se è JSON, lo processiamo
                batch = []
                for riga in dati:
                    batch.append({
                        "id_gara_fisi": id_gara,
                        "atleta_nome": riga.get("nominativo") or riga.get("atleta_nome"),
                        "posizione": riga.get("posizione"),
                        "societa": riga.get("societa_desc")
                    })
                if batch:
                    supabase.table("Risultati").upsert(batch).execute()
                    print(f"   ✅ Gara {id_gara}: Inseriti {len(batch)} atleti (JSON)")
            
            except:
                # Se non è JSON, probabilmente è un pezzo di HTML (molto comune)
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(r.text, 'html.parser')
                rows = soup.find_all('tr')
                batch = []
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 4:
                        d = [c.get_text(strip=True) for c in cols]
                        if d[0].isdigit(): # Se la prima colonna è la posizione
                            batch.append({
                                "id_gara_fisi": id_gara,
                                "posizione": int(d[0]),
                                "atleta_nome": d[2], # Di solito il nome è qui
                                "societa": d[4] if len(d) > 4 else ""
                            })
                
                if batch:
                    supabase.table("Risultati").upsert(batch).execute()
                    print(f"   ✅ Gara {id_gara}: Inseriti {len(batch)} atleti (HTML)")
                else:
                    print(f"   ⚠️ Gara {id_gara}: Dati ricevuti ma formato non riconosciuto.")

        except Exception as e:
            print(f"   ❌ Errore gara {id_gara}: {e}")

if __name__ == "__main__":
    scarica_risultati_atleti()
