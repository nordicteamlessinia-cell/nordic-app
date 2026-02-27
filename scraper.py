import os
import time
import hashlib
import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client

# ---------------------------------------------------------
# CONFIG SUPABASE
# ---------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://YOUR_PROJECT.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "YOUR_SERVICE_ROLE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

CALENDAR_URL = "https://comitati.fisi.org/veneto/calendario/"


# ---------------------------------------------------------
# HASH EVENTO PER EVITARE DUPLICATI
# ---------------------------------------------------------
def hash_event(e):
    raw = f"{e['date']}-{e['location']}-{e['race']}-{e['category']}-{e.get('link', '')}"
    return hashlib.md5(raw.encode()).hexdigest()


# ---------------------------------------------------------
# SCARICA PAGINA CALENDARIO
# ---------------------------------------------------------
def fetch_calendar_page():
    r = requests.get(CALENDAR_URL)
    r.raise_for_status()
    return r.text


# ---------------------------------------------------------
# PARSE CALENDARIO
# ---------------------------------------------------------
def parse_calendar(html):
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("table tbody tr")
    events = []

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 5:
            continue

        date = cols[0].get_text(strip=True)
        location = cols[1].get_text(strip=True)
        race = cols[2].get_text(strip=True)
        category
