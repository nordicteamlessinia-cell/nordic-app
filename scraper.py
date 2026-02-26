import os
from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

def test_connessione():
    print(f"Tentativo di connessione a: {url}")
    dati_test = {
        "atleta_nome": "TEST CONNESSIONE",
        "societa": "GITHUB ACTIONS",
        "posizione": 1,
        "id_gara_fisi": "999999"
    }
    try:
        res = supabase.table("gare").insert(dati_test).execute()
        print("✅ INSERIMENTO RIUSCITO:", res)
    except Exception as e:
        print("❌ ERRORE DURANTE L'INSERIMENTO:", e)

if __name__ == "__main__":
    test_connessione()
