import os
import requests
import time
import datetime
from bs4 import BeautifulSoup
from supabase import create_client

# 🟢 INIZIALIZZAZIONE SUPABASE
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'}

# 🗺️ DIZIONARIO NAZIONALE DEGLI SLUG WEB
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
        p = data_gara.split("/")
        if len(p) == 3:
            return str(int(p[2]) + 1) if int(p[1]) >= 6 else str(p[2])
    except: pass
    return "2026"

# =====================================================================
# 🗓️ FASE 1: SPIDER DEI CALENDARI HTML (Il nostro filtro Infallibile)
# =====================================================================
def spider_calendari_fondo_nazionale():
    print("\n--- 📅 FASE 1: DOWNLOAD CALENDARI STORICI (SOLO FONDO) ---")
    
    anno_corrente = datetime.datetime.now().year
    mese_corrente = datetime.datetime.now().month
    anno_massimo = anno_corrente + 1 if mese_corrente >= 6 else anno_corrente
    stagioni_da_scaricare = list(range(2020, anno_massimo + 1))
    
    for nome_comitato, slug_sito in COMITATI_FISI.items():
        print(f"\n🌍 Cerco le gare per: {nome_comitato}...")
        
        percorso_base = "calendario"
        gare_totali_comitato = 0
        
        for anno in stagioni_da_scaricare:
            pagina_corrente = 1
            id_gia_visti = set()
            
            while True:
                # Costruiamo l'URL passando sia l'anno (?d=ANNO) sia la pagina
                if pagina_corrente == 1:
                    url_calendario = f"https://comitati.fisi.org/{slug_sito}/{percorso_base}/?d={anno}"
                else:
                    url_calendario = f"https://comitati.fisi.org/{slug_sito}/{percorso_base}/?d={anno}&paged={pagina_corrente}"
                
                try:
                    res = requests.get(url_calendario, headers=HEADERS, timeout=15)
                    
                    # Se dà 404, proviamo con calendario-gare (solo alla prima pagina per capire il sito)
                    if res.status_code == 404 and pagina_corrente == 1 and percorso_base == "calendario":
                        percorso_base = "calendario-gare"
                        url_calendario = f"https://comitati.fisi.org/{slug_sito}/{percorso_base}/?d={anno}"
                        res = requests.get(url_calendario, headers=HEADERS, timeout=15)
                    
                    # Se dà ANCORA 404, abbiamo finito le pagine di questo anno
                    if res.status_code == 404:
                        break
                        
                    if res.status_code != 200:
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
                        
                        # 🎯 IL NOSTRO FILTRO INFALLIBILE!
                        testo_riga_intero = riga.get_text().upper()
                        if "FONDO" not in testo_riga_intero and "NORDICO" not in testo_riga_intero and "CROSS COUNTRY" not in testo_riga_intero:
                            continue 
                        
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
                                "comitato": nome_comitato
                            })
                        except Exception:
                            continue
                    
                    # Se non c'è nessuna nuova gara in questa pagina, interrompi la paginazione per questo anno
                    if not nuove_gare_nella_pagina and len(batch_gare) == 0:
                        if len(righe) < 2: 
                            break
                        
                    if batch_gare:
                        supabase.table("Gare").upsert(batch_gare).execute()
                        gare_totali_comitato += len(batch_gare)
                        print(f"   📄 Anno {anno} - Pagina {pagina_corrente}: Salvate {len(batch_gare)} gare di FONDO.")
                        
                    time.sleep(0.5) 
                    pagina_corrente += 1
                    
                except Exception as e:
                    break
                    
        print(f"   🏁 Completato {nome_comitato}: {gare_totali_comitato} gare di FONDO trovate dal 2020 ad oggi.")

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
        
        url_comp = f"https://comitati.fisi.org/{slug_sito}/competizione/?idComp={id_comp}&d={stagione_fisi}"
        
        try:
            res = requests.get(url_comp, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            links = soup.find_all('a', href=True)
            id_sottogare = list(set([l['href'].split('idGara=')[1].split('&')[0] for l in links if 'idGara=' in l['href']]))
            
            if not id_sottogare:
                continue

            print(f"\n🟢 Analizzo: {nome_g} a {luogo_g} ({nome_comitato} | Data: {data_g})")

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
                    print(f"   ✅ Salvati {len(batch_atleti)} atleti per la gara!")
                
                time.sleep(0.3)

        except Exception as e:
            pass

if __name__ == "__main__":
    spider_calendari_fondo_nazionale()
    spider_atleti_master_con_tempo()
