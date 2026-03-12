import requests
import json

BASE_URL_AJAX = "https://comitati.fisi.org/wp-admin/admin-ajax.php"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def indagine_struttura_dati():
    print("🕵️‍♂️ FASE 0: INVESTIGAZIONE DEL DATABASE FISI...")
    
    params = {
        "action": "competizioni_get_all",
        "offset": 0,
        "limit": 5, # Ne prendiamo solo 5 per non intaserci
        "url": "https://comitati.fisi.org/veneto/calendario/",
        "idStagione": "2024", # Proviamo con l'anno scorso
        "disciplina": "", # Chiediamo tutto di proposito
        "dataInizio": "01/01/2010",
        "dataFine": "31/12/2030"
    }

    try:
        r = requests.get(BASE_URL_AJAX, params=params, headers=HEADERS, timeout=15)
        data = r.json()
        
        if not data:
            print("Nessun dato ricevuto.")
            return

        print(f"\n✅ Ricevute {len(data)} gare. Analizzo le prime 3 in formato RAW (grezzo):")
        
        for i, item in enumerate(data[:3]):
            print(f"\n{'='*40}")
            print(f"🎿 GARA {i+1}: {item.get('nome', 'Sconosciuta')}")
            print(f"{'='*40}")
            # Stampiamo TUTTO il dizionario formattato bene per leggerlo
            print(json.dumps(item, indent=4, ensure_ascii=False))

    except Exception as e:
        print(f"❌ Errore durante l'indagine: {e}")

if __name__ == "__main__":
    indagine_struttura_dati()
