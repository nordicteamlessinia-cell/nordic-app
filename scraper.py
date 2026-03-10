import os
import requests
import time
from bs4 import BeautifulSoup
from supabase import create_client

# Configurazione Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'}

# 🗺️ DIZIONARIO DEFINITIVO DEGLI SLUG WEB
COMITATI_FISI = {
    'Abruzzo (CAB)': 'abruzzo',
    'Alto Adige (AA)': 'alto-adige',           
    'Alpi Centrali (AC)': 'alpi-centrali',     
    'Alpi Occidentali (AOC)': 'alpi-occidentali', 
    'Appennino Emiliano (CAE)': 'appennino-emiliano', 
    'Appennino Toscano (CAT)': 'appennino-toscano',   
    'Calabro Lucano (CAL)': 'calabro-lucano',
    'Campano (CAM)': 'campano',
    'Friuli Venezia Giulia (FVG)': 'friuli-venezia-giulia', 
    'Lazio e Sardegna (CLS)': 'lazio-sardegna',
    'Ligure (LIG)': 'ligure',
    'Pugliese (PUG)': 'pugliese',
    'Siculo (SIC)': 'siculo',
    'Trentino (TN)': 'trentino',
    'Umbro Marchigiano (CUM)': 'umbro-marchigiano',
    'Valdostano (ASIVA)': 'asiva',
    'Veneto (VE)': 'veneto'
}

def calcola_stagione_fisi(data_gara):
    try:
        if not data_gara or data_gara == "N/D": return "2026"
        if "-" in data_gara:
            p = data_gara.split("-")
            anno = int(p[0])
            mese = int(p[1])
        elif "/" in data_gara:
            p = data_gara.split("/")
            anno = int(p[2])
            mese = int(p[1])
        else:
            return "2026"
        return str(anno + 1) if mese >= 6 else str(anno)
    except: 
        return "2026"

# =====================================================================
# 🗓️ FASE 1: SPIDER DEI CALENDARI (Paginazione + Filtro Testuale Fondo)
# =====================================================================
def spider_calendari_fondo_nazionale():
    print("\n--- 📅 FASE 1: DOWNLOAD CALENDARI NAZIONALI (FONDO) ---")
    
    for nome_comitato, slug_sito in COMITATI_FISI.items():
        print(f"\n🌍 Cerco le gare per: {nome_comitato}...")
        
        pagina_corrente = 1
        gare_totali_comitato = 0
        id_gia_visti = set()
        
        # Determiniamo il percorso base (calendario o calendario-gare)
        percorso_base = "calendario"
        
        while True:
            # URL Standard per la paginazione di WordPress
            url_calendario = f"https://comitati.fisi.org/{slug_sito}/{percorso_base}/?paged={pagina_corrente}"
            
            try:
                res = requests.get(url_calendario, headers=HEADERS, timeout=15)
                
                # Auto-correzione del link se il comitato usa "calendario-gare" (succede solo alla pagina 1)
                if res.status_code == 404 and pagina_corrente == 1 and percorso_base == "calendario":
                    percorso_base = "calendario-gare"
                    url_calendario = f"https://comitati.fisi.org/{slug_sito}/{percorso_base}/?paged={pagina_corrente}"
                    res = requests.get(url_calendario, headers=HEADERS, timeout=15)
                
                # Se dà ANCORA 404, significa che abbiamo superato l'ultima pagina disponibile! Interrompiamo il ciclo.
                if res.status_code == 404:
                    break
                    
                if res.status_code != 200:
                    print(f"   ❌ Errore server {res.status_code}")
                    break
                    
                soup = BeautifulSoup(res.text, 'html.parser')
                righe = soup.find_all('tr')
                
                batch_gare = []
                nuove_gare_nella_pagina = False
                
                for riga in righe:
                    colonne = riga.find_all('td')
                    if len(colonne) < 3: continue
                    
                    link_tag = riga.find('a', href=True)
                    if not link_tag or 'idComp=' not in link_tag['href']: continue
                    
                    # 🎯 IL FILTRO MAGICO: Salviamo solo se nella riga si parla di Fondo
                    testo_riga_intero = riga.get_text().upper()
                    if "FONDO" not in testo_riga_intero and "NORDICO" not in testo_riga_intero:
                        continue # Salta tutto lo Sci Alpino, Snowboard, ecc.
                    
                    try:
                        id_comp = link_tag['href'].split('idComp=')[1].split('&')[0]
                        
                        if id_comp in id_gia_visti: continue
                        id_gia_visti.add(id_comp)
                        nuove_gare_nella_pagina = True
                        
                        data_g = colonne[0].get_text(strip=True)
                        luogo_g = colonne[1].get_text(strip=True) if len(colonne) > 1 else "N/D"
                        nome_g = colonne[2].get_text(strip=True) if len(colonne) > 2 else "Gara FISI"
                        
                        batch_gare.append({
                            "id_gara_fisi": id_comp,
                            "data_gara": data_g,
                            "luogo": luogo_g,
                            "gara_nome": nome_g,
                            "comitato": nome_comitato,
                            "disciplina": "Sci di Fondo" 
                        })
                    except Exception as e:
                        continue
                
                # Se non ci sono più righe con 'idComp', abbiamo finito la tabella
                if not nuove_gare_nella_pagina and len(batch_gare) == 0:
                    # Controlliamo se ci sono righe in generale. Se no, fermati.
                    if len(righe) < 2: 
                        break
                    
                if batch_gare:
                    supabase.table("Gare").upsert(batch_gare).execute()
                    gare_totali_comitato += len(batch_gare)
                    print(f"   📄 Pagina {pagina_corrente}: Salvate {len(batch_gare)} gare di FONDO.")
                    
                time.sleep(0.5) 
                pagina_corrente += 1
                
            except Exception as e:
                print(f"   ❌ Errore alla pagina {pagina_corrente} di {nome_comitato}: {e}")
                break
                
        print(f"   🏁 Completato {nome_comitato}: {gare_totali_comitato} gare di FONDO trovate.")

# =====================================================================
# ⛷️ FASE 2: SPIDER DEGLI ATLETI
# =====================================================================
def spider_atleti_master_con_tempo():
    print("\n--- 📂 FASE 2: RECUPERO RISULTATI ATLETI DAL DATABASE... ---")
    gare_db = supabase.table("Gare").select("id_gara_fisi, data_gara, gara_nome, luogo, comitato").execute()
    lista_gare = gare_db.data

    print(f"--- ⏱️ INIZIO ESTRAZIONE ATLETI --- (Trovate {len(lista_gare)} gare nel DB)")

    for gara in lista_gare:
        id_comp = gara.get('id_gara_fisi')
        data_g = gara.get('data_gara')
        nome_g = gara.get('gara_nome')
        luogo_g = gara.get('luogo')
        nome_comitato = gara.get('comitato')
        
        if not id_comp or not nome_comitato or nome_comitato == 'Generico': 
            continue
            
        slug_sito = COMITATI_FISI.get(nome_comitato)
        if not slug_sito: 
            continue
        
        stagione_fisi = calcola_stagione_fisi(data_g)
        print(f"\n🟢 Analizzo: {nome_g} a {luogo_g} ({nome_comitato} | Data: {data_g})")
        
        url_comp = f"https://comitati.fisi.org/{slug_sito}/competizione/?idComp={id_comp}&d={stagione_fisi}"
        
        try:
            res = requests.get(url_comp, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            links = soup.find_all('a', href=True)
            id_sottogare = list(set([l['href'].split('idGara=')[1].split('&')[0] for l in links if 'idGara=' in l['href']]))
            
            if not id_sottogare:
                print("   ⏩ Nessuna classifica trovata.")
                continue

            for id_g in id_sottogare:
                url_gara = f"https://comitati.fisi.org/{slug_sito}/gara/?idGara={id_g}&idComp={id_comp}&d={stagione_fisi}"
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
                            "comitato": nome_comitato 
                        })
                        i += 8
                    else:
                        i += 1
                
                if batch_atleti:
                    supabase.table("Risultati").upsert(batch_atleti).execute()
                    print(f"   ✅ Salvati {len(batch_atleti)} atleti per ID {id_g}")
                
                time.sleep(0.5)

        except Exception as e:
            print(f"   ❌ Errore sull'evento {id_comp}: {e}")

if __name__ == "__main__":
    spider_calendari_fondo_nazionale()
    spider_atleti_master_con_tempo()
