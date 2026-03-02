import requests

BASE_URL = "https://comitati.fisi.org/wp-admin/admin-ajax.php"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def detective_discipline():
    print("--- 🕵️ INIZIO INDAGINE DISCIPLINE (Stagione 2025) ---")
    params = {
        "action": "competizioni_get_all",
        "offset": 0,
        "limit": 500, # Prendiamo una bella fettona di gare in un colpo solo
        "url": "https://comitati.fisi.org/veneto/calendario/",
        "idStagione": "2025", 
        "disciplina": "" 
    }
    
    try:
        r = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=30)
        data = r.json()
        
        if not data:
            print("Nessun dato trovato per il 2025.")
            return
            
        conteggio = {}
        for item in data:
            # Peschiamo il campo disciplina esatto che ci manda il server
            disc = str(item.get("disciplina", "SCONOSCIUTA"))
            conteggio[disc] = conteggio.get(disc, 0) + 1
            
        print(f"\n✅ Trovate {len(data)} gare totali nel 2025. Ecco le etichette segrete della FISI:")
        for d, count in conteggio.items():
            print(f"   🏷️ Disciplina: '{d}'  --->  Gare trovate: {count}")
            
    except Exception as e:
        print(f"❌ Errore: {e}")

if __name__ == "__main__":
    detective_discipline()
