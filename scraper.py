import os
import requests
import time
from bs4 import BeautifulSoup
from supabase import create_client

# 🟢 INIZIALIZZAZIONE SUPABASE (Tramite i Secrets di GitHub)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'}

# 🗺️ IL DIZIONARIO NAZIONALE: Mappa il nome del DB con lo slug dell'URL
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

# 🛠️ FUNZIONE DATE CORRETTA: Legge sia il formato Supabase (YYYY-MM-DD) che le sbarre
def calcola_stagione_fisi(data_gara):
    try:
        if not data_gara or data_gara == "N/D": return "2026"
        
        # Formato Supabase: 2024-03-12
        if "-" in data_gara:
            p = data_gara.split("-")
            anno = int(p[0])
            mese = int(p[1])
        # Formato classico: 12/03/2024
        elif "/" in data_gara:
            p = data_gara.split("/")
            anno = int(p[2])
            mese = int(p[1])
        else:
            return "2026"
            
        # Logica FISI: La stagione 2024 inizia a Giugno 2023.
        return str(anno + 1) if mese >= 6 else str(anno)
    except: 
        return "2026"

def spider_atleti_master_con_tempo():
    print("--- 📂 RECUPERO LE GARE DAL DATABASE... ---")
    
    # 🎯 ESTRAIAMO ANCHE LA COLONNA 'comitato'
    gare_db = supabase.table("Gare").select("id_gara_fisi, data_gara, gara_nome, luogo, comitato").execute()
    lista_gare = gare_db.data

    print(f"--- ⏱️ INIZIO ESTRAZIONE ATLETI --- (Trovate {len(lista_gare)} gare)")

    for gara in lista_gare:
        id_comp = gara.get('id_gara_fisi')
        data_g = gara.get('
