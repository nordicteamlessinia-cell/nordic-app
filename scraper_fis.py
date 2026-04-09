import os
import time
import requests
import datetime
from bs4 import BeautifulSoup
from supabase import create_client

# 🟢 INIZIALIZZAZIONE SUPABASE
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ ERRORE: Variabili di ambiente Supabase mancanti!")
    exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def formatta_data_fis(testo_data):
    """Converte date della FIS nel formato YYYY-MM-DD per il database"""
    if not testo_data or testo_data == "N/D":
        return datetime.datetime.now().strftime("%Y-%m-%d")
    
    try:
        clean_date = testo_data.split('\n')[0].strip()
        for fmt in ("%B %d, %Y", "%d %b %Y", "%d.%m.%Y", "%Y-%m-%d"):
            try:
                return datetime.datetime.strptime(clean_date, fmt).strftime("%Y-%m-%d")
            except:
                continue
    except:
        pass
    return datetime.datetime.now().strftime("%Y-%m-%d")

def estrai_e_salva_gara(raceid):
    url = f"https://www.fis-ski.com/DB/general/results.html?sectorcode=CC&raceid={raceid}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }

    print(f"🚀 Elaborazione gara FIS {raceid}...")
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Errore API: HTTP {response.status_code}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # --- 1. ESTRAZIONE DATI GENERALI DELLA GARA (TESTATA) ---
    try:
        # Il luogo è solitamente nell'h1 dentro .event-header__name
        h1_tag = soup.select_one(".event-header__name h1")
        luogo = h1_tag.text.strip() if h1_tag else "N/D"
        
        # La data
        date_tag = soup.select_one(".date__full")
        data_raw = date_tag.text.strip() if date_tag else "N/D"
        data_gara = formatta_data_fis(data_raw)
        
        # Categoria e Specialità (es. World Cup / Sprint Free)
        cat_tag = soup.select_one(".event-header__kind")
        categoria = cat_tag.text.strip() if cat_tag else "FIS"
        
        spec_tag = soup.select_one(".event-header__subtitle")
        specialita = spec_tag.text.strip() if spec_tag else "Cross-Country"
        
        print(f"📍 Info Gara: {luogo} | 📅 Data: {data_gara} | 🎿 {categoria} - {specialita}")
        
    except Exception as e:
        print(f"⚠️ Errore nell'estrazione dell'intestazione: {e}")
        luogo, data_gara, categoria, specialita = "N/D", datetime.datetime.now().strftime("%Y-%m-%d"), "FIS", "Cross-Country"

    # --- 2. ESTRAZIONE ATLETI ---
    righe_atleti = soup.find_all("a", class_="table-row")
    
    if not righe_atleti:
        print("⚠️ Nessun atleta trovato.")
        return

    risultati_da_salvare = []

    for riga in righe_atleti:
        try:
            nome_tag = riga.find("div", class_="athlete-name")
            nazione_tag = riga.find("span", class_="country__name-short")
            
            nome = nome_tag.text.strip() if nome_tag else "N/D"
            nazione = nazione_tag.text.strip() if nazione_tag else "N/D"
            
            colonne = [col.text.strip() for col in riga.find_all("div") if col.text.strip()]
            
            posizione = colonne[0] if len(colonne) > 0 else "N/D"
            codice_fis = colonne[1] if len(colonne) > 1 else "N/D" 
            tempo = colonne[-2] if len(colonne) > 2 else "N/D"
            punti = colonne[-1] if len(colonne) > 2 else "0.00"
            
            record = {
                "id_gara_fis": str(raceid),
                "luogo": luogo,              # 👈 AGGIUNTO!
                "data_gara": data_gara,      # 👈 AGGIUNTO (già formattato YYYY-MM-DD)!
                "categoria": categoria,      # 👈 AGGIUNTO!
                "specialita": specialita,    # 👈 AGGIUNTO!
                "posizione": posizione,
                "codice_fis": codice_fis,
                "atleta_nome": nome,
                "nazione": nazione,
                "tempo": tempo,
                "punti_fis": punti,
                "comitato": "FIS"
            }
            risultati_da_salvare.append(record)
            
        except Exception as e:
            continue

    # --- 3. SALVATAGGIO SU SUPABASE ---
    if risultati_da_salvare:
        try:
            supabase.table("Risultati_Fis").upsert(risultati_da_salvare).execute()
            print(f"✅ {len(risultati_da_salvare)} atleti salvati correttamente su Supabase con Luogo e Data!")
        except Exception as e:
            print(f"❌ Errore Supabase: {e}")

if __name__ == "__main__":
    estrai_e_salva_gara(50468)
