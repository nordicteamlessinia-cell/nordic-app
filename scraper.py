import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import datetime
import re
from supabase import create_client

# 🟢 INIZIALIZZAZIONE SUPABASE
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 🛡️ ARMATURA DI RETE
session = requests.Session()
retries = Retry(total=5, backoff_factor=2, status_forcelist=[ 429, 500, 502, 503, 504 ])
session.mount('https://', HTTPAdapter(max_retries=retries))
session.mount('http://', HTTPAdapter(max_retries=retries))
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})

BASE_URL_AJAX = "https://comitati.fisi.org/wp-admin/admin-ajax.php"

# 🥇 LA FILA INDIANA
COMITATI_FISI = {
    'trentino': 'Trentino (TN)', 'alto-adige': 'Alto Adige (AA)', 'veneto': 'Veneto (VE)',
    'alpi-centrali': 'Alpi Centrali (AC)', 'alpi-occidentali': 'Alpi Occidentali (AOC)',
    'friuli-venezia-giulia': 'Friuli Venezia Giulia (FVG)', 'appennino-emiliano': 'Appennino Emiliano (CAE)',
    'appennino-toscano': 'Appennino Toscano (CAT)', 'abruzzo': 'Abruzzo (CAB)',
    'lazio-sardegna': 'Lazio e Sardegna (CLS)', 'umbro-marchigiano': 'Umbro Marchigiano (CUM)',
    'campano': 'Campano (CAM)', 'calabro-lucano': 'Calabro Lucano (CAL)',
    'pugliese': 'Pugliese (PUG)', 'siculo': 'Siculo (SIC)',
    'ligure': 'Ligure (LIG)', 'asiva': 'Valdostano (ASIVA)'
}

# 🎯 DECODER COMITATI 
MAPPA_NOMI_COMITATI = {
    'TRENTINO': 'Trentino (TN)', 'TN': 'Trentino (TN)',
    'ALTO ADIGE': 'Alto Adige (AA)', 'AA': 'Alto Adige (AA)', 'SUDTIROL': 'Alto Adige (AA)', 'BZ': 'Alto Adige (AA)',
    'VENETO': 'Veneto (VE)', 'VE': 'Veneto (VE)',
    'ALPI CENTRALI': 'Alpi Centrali (AC)', 'AC': 'Alpi Centrali (AC)',
    'ALPI OCCIDENTALI': 'Alpi Occidentali (AOC)', 'AOC': 'Alpi Occidentali (AOC)',
    'VALDOSTANO': 'Valdostano (ASIVA)', 'ASIVA': 'Valdostano (ASIVA)', 'VDA': 'Valdostano (ASIVA)',
    'FRIULI VENEZIA GIULIA': 'Friuli Venezia Giulia (FVG)', 'FVG': 'Friuli Venezia Giulia (FVG)',
    'APPENNINO EMILIANO': 'Appennino Emiliano (CAE)', 'CAE': 'Appennino Emiliano (CAE)',
    'APPENNINO TOSCANO': 'Appennino Toscano (CAT)', 'CAT': 'Appennino Toscano (CAT)',
    'ABRUZZO': 'Abruzzo (CAB)', 'CAB': 'Abruzzo (CAB)',
    'LAZIO E SARDEGNA': 'Lazio e Sardegna (CLS)', 'CLS': 'Lazio e Sardegna (CLS)',
    'LIGURE': 'Ligure (LIG)', 'LIG': 'Ligure (LIG)', 'LI': 'Ligure (LIG)',
    'UMBRO MARCHIGIANO': 'Umbro Marchigiano (CUM)', 'CUM': 'Umbro Marchigiano (CUM)',
    'CAMPANO': 'Campano (CAM)', 'CAM': 'Campano (CAM)', 'MOL': 'Campano (CAM)',
    'CALABRO LUCANO': 'Calabro Lucano (CAL)', 'CAL': 'Calabro Lucano (CAL)',
    'PUGLIESE': 'Pugliese (PUG)', 'PUG': 'Pug
