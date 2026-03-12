import os
import requests
import time
from bs4 import BeautifulSoup
from supabase import create_client

# 🟢 INIZIALIZZAZIONE SUPABASE
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'}
BASE_URL_AJAX = "https://comitati.fisi.org/wp-admin/admin-ajax.php"

def calcola_stagione_fisi(data_gara):
    try:
        if not data_gara or data_gara == "N/D": return "2026"
        p = data_gara.split("/")
        if len(p) == 3:
            return str(int(p[2]) + 1) if int(p[1]) >= 6 else str(p[2])
    except: pass
    return "2026"

# =====================================================================
# 🗓️ FASE 1: DOWNLOAD CALENDARIO (SOLO VENETO E SOLO FONDO)
# =====================================================================
def avvia_estrazione_calendario_veneto():
    print("--- 🚀 FASE 1: DOWNLOAD CALENDARIO VENETO ---")
    
    params = {
        "action": "competizioni_get_all",
        "offset": 0,
        "limit": 100,
        "url": "https://comitati.fisi.org/veneto/calendario/?dis=F", # 🎯 Filtro Fondo attivato!
        "idStagione": "2025", 
        "disciplina": "",
        "dataInizio": "01/06/2024",
        "dataFine": "30/05/2026"
    }

    all_gare = []
    
    try:
        while True:
            r = requests.get(BASE_URL_AJAX, params=params, headers=HEADERS, timeout=30)
            data = r.json()
            if not data: break

            for item in data:
                record = {
                    "id_gara_fisi": str(item.get("idCompetizione")), 
                    "gara_nome": item.get("nome"),
                    "luogo": item.get("comune", "N/D"), # 🎯 Sbloccato!
                    "data_gara": item.get("dataInizio", "N/D"), # 🎯 Sbloccato!
                    "comitato": "Veneto (VE)"
                }
                all_gare.append(record)
                
            params["offset"] += params["limit"]
            print(f"   Scaricati {len(all_gare)} record competizioni...")

        if all_gare:
            print(f"--- 💾 INVIO {len(all_gare)} RECORD A SUPABASE ---")
            supabase.table("Gare").upsert(all_gare).execute()
            print("--- ✅ SUCCESSO: CALENDARIO CARICATO! ---\n")
            
    except Exception as e:
        print(f"--- ❌ ERRORE FASE 1: {e} ---\n")

# =====================================================================
# ⛷️ FASE 2: ESTRAZIONE ATLETI (DALLE GARE APPENA SCARICATE)
# =====================================================================
def spider_atleti_master_con_tempo():
    print("--- 📂 FASE 2: RECUPERO LE GARE DAL DATABASE... ---")
    
    # 🎯 Leggiamo solo le gare del Veneto per sicurezza
    gare_db = supabase.table("Gare").select("id_gara_fisi, data_gara, gara_nome, luogo").eq("comitato", "Veneto (VE)").execute()
    lista_gare = gare_db.data

    print(f"--- ⏱️ INIZIO ESTRAZIONE ATLETI ({len(lista_gare)} gare trovate) ---")

    for gara in lista_gare:
        id_comp = gara.get('id_gara_fisi')
        data_g = gara.get('data_gara')
        nome_g = gara.get('gara_nome')
        luogo_g = gara.get('luogo')
        
        if not id_comp: continue
        
        stagione_fisi = calcola_stagione_fisi(data_g)
        print(f"\n🟢 Analizzo: {nome_g} a {luogo_g} (Data: {data_g})")
        
        url_comp = f"https://comitati.fisi.org/veneto/competizione/?idComp={id_comp}&d={stagione_fisi}"
        
        try:
            res = requests.get(url_comp, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            links = soup.find_all('a', href=True)
            id_sottogare = list(set([l['href'].split('idGara=')[1].split('&')[0] for l in links if 'idGara=' in l['href']]))
            
            if not id_sottogare:
                print("   ⏩ Nessuna classifica trovata.")
                continue

            for id_g in id_sottogare:
                url_gara = f"https://comitati.fisi.org/veneto/gara/?idGara={id_g}&idComp={id_comp}&d={stagione_fisi}"
                r_data = requests.get(url_gara, headers=HEADERS, timeout=15)
                gara_soup = BeautifulSoup(r_data.text, 'html.parser')
                
                # ESTRAZIONE CATEGORIA E SPECIALITÀ
                testi_completi = list(gara_soup.stripped_strings)
                cat, spec = "", ""
                for i, t in enumerate(testi_completi):
                    testo_upper = t.upper()
                    if "CATEGORIA" == testo_upper and i + 1 < len(testi_completi) and testi_completi[i+1].upper() != "POS.":
                        cat = testi_completi[i+1]
                    if "SPECIALITÀ" in testo_upper or "SPECIALITA" in testo_upper:
                        if i + 1 < len(testi_completi) and testi_completi[i+1].upper() != "CATEGORIA":
                            spec = testi_completi[i+1]
                            
                categoria_finale = f"{spec} - {cat}".strip(" -") if spec or cat else "Generale"

                # ESTRAZIONE ATLETI E TEMPI
                elementi_atleti = gara_soup.find_all('span', class_='x-text-content-text-primary')
                testi_atleti = [e.get_text(strip=True) for e in elementi_atleti if len(e.get_text(strip=True)) > 0]
                
                batch_atleti = []
                i = 0
                while i < len(testi_atleti) - 7:
                    if testi_atleti[i].isdigit() and testi_atleti[i+1].isdigit() and len(testi_atleti[i+1]) >= 3:
                        batch_atleti.append({
                            "id_gara_fisi": id_g, 
                            "id_comp_collegata": id_comp, 
                            "posizione": int(testi_atleti[i]),
                            "atleta_nome": testi_atleti[i+2],
                            "societa": testi_atleti[i+4],
                            "tempo": testi_atleti[i+5], 
                            "categoria": categoria_finale,
                            "gara_nome": nome_g,
                            "luogo": luogo_g,
                            "data_gara": data_g,
                            "comitato": "Veneto (VE)" # 🎯 Aggiunto per completezza
                        })
                        i += 8
                    else:
                        i += 1
                
                if batch_atleti:
                    supabase.table("Risultati").upsert(batch_atleti).execute()
                    print(f"   ✅ Salvati {len(batch_atleti)} atleti con i loro Tempi Gara!")
                
                time.sleep(0.5)

        except Exception as e:
            print(f"   ❌ Errore sull'evento {id_comp}: {e}")

if __name__ == "__main__":
    avvia_estrazione_calendario_veneto()
    spider_atleti_master_con_tempo()
