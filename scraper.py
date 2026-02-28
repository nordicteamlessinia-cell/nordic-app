import requests
import json

BASE_URL = "https://comitati.fisi.org/wp-admin/admin-ajax.php"

def esplora_api():
    params = {
        "action": "competizioni_get_all",
        "offset": 0,
        "limit": 1, # Chiediamo SOLO 1 record per analizzarlo
        "url": "https://comitati.fisi.org/veneto/calendario/",
        "idStagione": "2025", 
        "disciplina": "",
        "dataInizio": "01/06/2024",
        "dataFine": "30/05/2026"
    }

    print("--- 🔦 ACCENDO LA TORCIA SULL'API ---")
    
    try:
        r = requests.get(BASE_URL, params=params, timeout=15)
        data = r.json()
        
        if data:
            print("\n--- 🎯 ECCO COSA CI MANDA DAVVERO IL SITO FISI: ---")
            # Stampiamo il dizionario formattato in modo leggibile
            print(json.dumps(data[0], indent=4))
            print("---------------------------------------------------")
            print("Cerca nel testo qui sopra il numero a 5 cifre (es. 56782).")
            print("Come si chiama l'etichetta alla sua sinistra?")
        else:
            print("Nessun dato ricevuto.")
            
    except Exception as e:
        print(f"Errore: {e}")

if __name__ == "__main__":
    esplora_api()
