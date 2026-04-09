import os
import time
import requests
from bs4 import BeautifulSoup
from supabase import create_client

# 🟢 INIZIALIZZAZIONE SUPABASE
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERRORE: Variabili di ambiente Supabase mancanti!")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def estrai_e_salva_gara(raceid):
    url = f"https://www.fis-ski.com/DB/general/results.html?sectorcode=CC&raceid={raceid}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    print(f"🚀 Elaborazione gara FIS {raceid}...")
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Errore di connessione: {response.status_code}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    righe_atleti = soup.find_all("a", class_="table-row")
    
    if not righe_atleti:
        print("⚠️ Nessun atleta trovato. La classifica potrebbe non essere ancora disponibile.")
        return

    risultati_da_salvare = []

    for riga in righe_atleti:
        try:
            nome_tag = riga.find("div", class_="athlete-name")
            nazione_tag = riga.find("span", class_="country__name-short")
            
            nome = nome_tag.text.strip() if nome_tag else "N/D"
            nazione = nazione_tag.text.strip() if nazione_tag else "N/D"
            
            # Estraiamo le colonne per prendere posizione, codice FIS, ecc.
            colonne = [col.text.strip() for col in riga.find_all("div") if col.text.strip()]
            
            # ATTENZIONE: adatta questi indici in base a come sono strutturate le colonne su FIS
            posizione = colonne[0] if len(colonne) > 0 else "N/D"
            codice_fis = colonne[1] if len(colonne) > 1 else "N/D" 
            tempo = colonne[-2] if len(colonne) > 2 else "N/D" # Spesso è la penultima colonna
            punti = colonne[-1] if len(colonne) > 2 else "0.00" # Spesso è l'ultima colonna
            
            # Creiamo il record formattato per Supabase
            record = {
                "id_gara_fis": str(raceid),
                "posizione": posizione,
                "codice_fis": codice_fis,
                "atleta_nome": nome,
                "nazione": nazione,
                "tempo": tempo,
                "punti_fis": punti,
                # Aggiungi qui altre colonne (es. data_gara) se le estrai dalla pagina
                "comitato": "FIS"
            }
            risultati_da_salvare.append(record)
            
        except Exception as e:
            continue

    print(f"🎯 Pronti da salvare: {len(risultati_da_salvare)} atleti.")

    # 🟢 SALVATAGGIO SU SUPABASE
    if risultati_da_salvare:
        try:
            # Upsert usa la chiave primaria per aggiornare i record esistenti o crearne di nuovi
            res = supabase.table("Risultati_Fis").upsert(risultati_da_salvare).execute()
            print(f"✅ Operazione Supabase completata con successo!")
        except Exception as e:
            print(f"❌ Errore durante il salvataggio su Supabase: {e}")

if __name__ == "__main__":
    estrai_e_salva_gara(50468)
