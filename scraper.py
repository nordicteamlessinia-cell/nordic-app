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

def calcola_stagione_fisi(data_gara):
    try:
        if not data_gara or data_gara == "N/D": return "2026"
        p = data_gara.split("/")
        if len(p) == 3:
            return str(int(p[2]) + 1) if int(p[1]) >= 6 else str(p[2])
    except: pass
    return "2026"

# =====================================================================
# 🗓️ FASE 1: SPIDER HTML (USIAMO IL SITO NORMALE GIA' FILTRATO!)
# =====================================================================
def avvia_estrazione_calendario_veneto():
    print("--- 🚀 FASE 1: DOWNLOAD CALENDARIO (HTML FILTRATO DALLA FISI) ---")
    
    # URL del sito visibile agli utenti
    url_base = "https://comitati.fisi.org/veneto/calendario/"
    
    all_gare = []
    pagina_corrente = 1
    
    try:
        while True:
            # 🎯 IL TUO METODO: Usiamo i parametri dell'URL per far filtrare tutto alla FISI!
            # d=2025 (Stagione), dis=F (Fondo), paged=... (Pagina)
            url_calendario = f"{url_base}?d=2025&dis=F&paged={pagina_corrente}"
            
            res = requests.get(url_calendario, headers=HEADERS, timeout=15)
            
            # Se la pagina non esiste, significa che abbiamo finito le gare di questa stagione
            if res.status_code == 404 or res.status_code != 200:
                break
                
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Troviamo le righe della tabella del calendario
            righe = soup.find_all('tr')
            nuove_gare_trovate = False
            
            for riga in righe:
                colonne = riga.find_all('td')
                if len(colonne) < 3: continue # Salta le intestazioni
                
                # Cerca il link della gara per prendere l'ID
                link_tag = riga.find('a', href=True)
                if not link_tag or 'idComp=' not in link_tag['href']: continue
                
                id_comp = link_tag['href'].split('idComp=')[1].split('&')[0]
                data_g = colonne[0].get_text(strip=True)
                luogo_g = colonne[1].get_text(strip=True) if len(colonne) > 1 else "N/D"
                nome_g = colonne[2].get_text(strip=True) if len(colonne) > 2 else "Gara FISI"
                
                # Un piccolissimo controllo di sicurezza per stare tranquilli
                if "ALPINO" in riga.get_text().upper():
                    continue
                    
                nuove_gare_trovate = True
                
                record = {
                    "id_gara_fisi": id_comp, 
                    "gara_nome": nome_g,
                    "luogo": luogo_g,
                    "data_gara": data_g,
                    "comitato": "Veneto (VE)"
                }
                
                if record not in all_gare:
                    all_gare.append(record)
                    print(f"   🎿 Trovata: {nome_g} ({data_g})")
                    
            if not nuove_gare_trovate:
                break # Fine della tabella
                
            pagina_corrente += 1
            time.sleep(0.5) # Pausa educata per il server

        if all_gare:
            print(f"--- 💾 INVIO {len(all_gare)} GARE DI PURO FONDO A SUPABASE ---")
            supabase.table("Gare").upsert(all_gare).execute()
            print("--- ✅ SUCCESSO: CALENDARIO CARICATO! ---\n")
        else:
            print("--- ⏩ NESSUNA GARA TROVATA ---")
            
    except Exception as e:
        print(f"--- ❌ ERRORE FASE 1: {e} ---\n")

# =====================================================================
# ⛷️ FASE 2: ESTRAZIONE ATLETI DALLA CLASSIFICA
# =====================================================================
def spider_atleti_master_con_tempo():
    print("--- 📂 FASE 2: RECUPERO LE GARE DAL DATABASE... ---")
    
    gare_db = supabase.table("Gare").select("id_gara_fisi, data_gara, gara_nome, luogo").eq("comitato", "Veneto (VE)").execute()
    lista_gare = gare_db.data

    print(f"--- ⏱️ INIZIO ESTRAZIONE ATLETI ({len(lista_gare)} gare nel DB) ---")

    for gara in lista_gare:
        id_comp = gara.get('id_gara_fisi')
        data_g = gara.get('data_gara')
        nome_g = gara.get('gara_nome')
        luogo_g = gara.get('luogo')
        
        if not id_comp: continue
        
        stagione_fisi = calcola_stagione_fisi(data_g)
        print(f"\n🟢 Analizzo: {nome_g} a {luogo_g}")
        
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
                            "comitato": "Veneto (VE)"
                        })
                        i += 8
                    else:
                        i += 1
                
                if batch_atleti:
                    supabase.table("Risultati").upsert(batch_atleti).execute()
                    print(f"   ✅ Salvati {len(batch_atleti)} atleti con Tempi Gara!")
                
                time.sleep(0.3)

        except Exception as e:
            print(f"   ❌ Errore sull'evento {id_comp}: {e}")

if __name__ == "__main__":
    avvia_estrazione_calendario_veneto()
    spider_atleti_master_con_tempo()
