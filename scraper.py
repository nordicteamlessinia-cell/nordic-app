import os
import requests
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BASE_URL = "https://comitati.fisi.org/wp-admin/admin-ajax.php"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def calendario_solo_fondo():
    print("--- 🚀 INIZIO SCARICAMENTO CALENDARIO (SOLO SCI DI FONDO 2020-2026) ---")
    all_gare = []
    
    # Scansioniamo dal 2020 al 2026
    for stagione in ["2020", "2021", "2022", "2023", "2024", "2025", "2026"]:
        print(f"\n📂 Cerco le gare di Fondo per la stagione {stagione}...")
        params = {
            "action": "competizioni_get_all",
            "offset": 0,
            "limit": 100,
            "url": "https://comitati.fisi.org/veneto/calendario/",
            "idStagione": stagione, 
            "disciplina": "CC"  # <--- FILTRO: Solo Cross Country (Fondo)
        }

        try:
            while True:
                r = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=30)
                data = r.json()
                
                if not data or len(data) == 0:
                    print(f"   🏁 Fine dati per la stagione {stagione}.")
                    break

                for item in data:
                    nome_gara = item.get("nome", "N/D")
                    disciplina_server = item.get("disciplina", "").upper()
                    
                    # Lo salviamo solo se è CC (Fondo)
                    if disciplina_server == "CC" or "FONDO" in nome_gara.upper():
                        record = {
                            "id_gara_fisi": str(item.get("idCompetizione")), 
                            "gara_nome": nome_gara,
                            "luogo": item.get("comune", "N/D"),       
                            "data_gara": item.get("dataInizio", "N/D") 
                        }
                        all_gare.append(record)

                params["offset"] += params["limit"]
                
        except Exception as e:
            print(f"❌ ERRORE SERVER SULLA STAGIONE {stagione}: {e}")

    # INVIO A SUPABASE
    if all_gare:
        try:
            print(f"\n--- 💾 STO INVIANDO {len(all_gare)} GARE DI FONDO A SUPABASE... ---")
            supabase.table("Gare").upsert(all_gare).execute()
            print(f"--- ✅ SUCCESSO! {len(all_gare)} GARE SALVATE NEL DATABASE! ---")
        except Exception as e:
            print(f"\n❌ ERRORE SUPABASE: {e}")
    else:
        print("\n⚠️ NESSUNA GARA DI FONDO TROVATA.")

if __name__ == "__main__":
    calendario_solo_fondo()
