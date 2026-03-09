import os
import requests
import time
import re
from bs4 import BeautifulSoup
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'}

# 🗺️ IL DIZIONARIO NAZIONALE
COMITATI_URL = {
    'Abruzzo (CAB)': 'abruzzo',
    'Alto Adige (AA)': 'altoadige',
    'Alpi Centrali (AC)': 'alpicentrali',
    'Alpi Occidentali (AOC)': 'aoc',
    'Appennino Emiliano (CAE)': 'cae',
    'Appennino Toscano (CAT)': 'cat',
    'Calabro Lucano (CAL)': 'cal',
    'Campano (CAM)': 'campano',
    'Friuli Venezia Giulia (FVG)': 'fvg',
    'Lazio e Sardegna (CLS)': 'cls',
    'Ligure (LIG)': 'ligure',
    'Pugliese (PUG)': 'pugliese',
    'Siculo (SIC)': 'siculo',
    'Trentino (TN)': 'trentino',
    'Umbro Marchigiano (CUM)': 'cum',
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
# 🗓️ FASE 1: SPIDER DEI CALENDARI (BULLDOZER MODE)
# =====================================================================
def spider_calendari_nazionale():
    print("\n--- 📅 INIZIO DOWNLOAD CALENDARI NAZIONALI ---")
    
    for nome_comitato, slug_sito in COMITATI_URL.items():
        print(f"\n🌍 Cerco le gare per il comitato: {nome_comitato}")
        
        # 💡 NOTA: Se vuoi solo le gare di Fondo, puoi aggiungere ?d=178 alla fine di questo URL
        url_calendario = f"https://comitati.fisi.org/{slug_sito}/calendario/"
        
        try:
            res = requests.get(url_calendario, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # Troviamo tutti i link cliccabili nella pagina
            links = soup.find_all('a', href=True)
            batch_gare = []
            id_gia_visti = set()
            
            for link in links:
                href = link['href']
                if 'idComp=' in href:
                    id_comp = href.split('idComp=')[1].split('&')[0]
                    
                    # Evitiamo i doppioni
                    if id_comp in id_gia_visti: continue
                    id_gia_visti.add(id_comp)
                    
                    # Estraiamo tutto il testo della "Card"
                    testo_card = link.get_text(separator=" | ", strip=True)
                    if len(testo_card) < 10:
                        testo_card = link.parent.get_text(separator=" | ", strip=True)
                        if len(testo_card) < 10:
                            testo_card = link.parent.parent.get_text(separator=" | ", strip=True)
                    
                    # 1. Troviamo la Data con una Regex infallibile
                    match_data = re.search(r'\d{2}/\d{2}/\d{4}', testo_card)
                    data_g = match_data.group(0) if match_data else "N/D"
                    
                    # 2. Puliamo il nome e luogo (prendiamo le stringhe più lunghe)
                    pezzi = [p.strip() for p in testo_card.split('|') if len(p.strip()) > 2]
                    
                    # Logica base: la disciplina di solito è il primo, il luogo il secondo
                    nome_g = pezzi[2] if len(pezzi) > 2 else "Gara FISI"
                    luogo_g = pezzi[1] if len(pezzi) > 1 else "Italia"
                    
                    batch_gare.append({
                        "id_gara_fisi": id_comp,
                        "data_gara": data_g,
                        "luogo": luogo_g,
                        "gara_nome": nome_g,
                        "comitato": nome_comitato # 🎯 ASSEGNAZIONE FONDAMENTALE DEL COMITATO
                    })
            
            # Salviamo nel database
            if batch_gare:
                supabase.table("Gare").upsert(batch_gare).execute()
                print(f"   ✅ Salvate {len(batch_gare)} gare nel calendario {nome_comitato}!")
            else:
                print(f"   ⏩ Nessuna gara trovata nel calendario {nome_comitato}.")
                
            time.sleep(0.5) 
            
        except Exception as e:
            print(f"   ❌ Errore scaricando il calendario di {nome_comitato}: {e}")

# =====================================================================
# ⛷️ FASE 2: SPIDER DEGLI ATLETI
# =====================================================================
def spider_atleti_master_con_tempo():
    print("\n--- 📂 RECUPERO LE GARE DAL DATABASE... ---")
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
            
        slug_sito = COMITATI_URL.get(nome_comitato)
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
    spider_calendari_nazionale()
    spider_atleti_master_con_tempo()
