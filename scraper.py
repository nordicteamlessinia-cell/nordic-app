import os
import time
import hashlib
import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://YOUR_PROJECT.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "YOUR_SERVICE_ROLE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

CALENDAR_URL = "https://comitati.fisi.org/veneto/calendario/"

def hash_event(e):
    raw = f"{e['date']}-{e['location']}-{e['race']}-{e['category']}-{e.get('link', '')}"
    return hashlib.md5(raw.encode()).hexdigest()

def fetch_calendar_page():
    r = requests.get(CALENDAR_URL)
    r.raise_for_status()
    return r.text

def parse_calendar(html):
    soup = BeautifulSoup(html, "html.parser")

    # DEBUG: salva HTML per controllare
    with open("debug_calendar.html", "w") as f:
        f.write(html)

    rows = soup.select("table tr")  # più robusto
    events = []

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 5:
            continue

        event = {
            "date": cols[0].get_text(strip=True),
            "location": cols[1].get_text(strip=True),
            "race": cols[2].get_text(strip=True),
            "category": cols[3].get_text(strip=True),
            "link": cols[4].find("a")["href"] if cols[4].find("a") else None
        }
        event["event_hash"] = hash_event(event)
        events.append(event)

    return events

def main():
    print("SUPABASE_URL:", SUPABASE_URL)
    print("SUPABASE_KEY PRESENTE:", SUPABASE_KEY is not None)

    html = fetch_calendar_page()
    events = parse_calendar(html)

    print("DEBUG EVENTS:", events)

    test_insert = supabase.table("sci_eventi").insert({
        "date": "2024-01-01",
        "location": "Test",
        "race": "Test",
        "category": "Test",
        "link": "https://example.com",
        "event_hash": "TEST123"
    }).execute()

    print("DEBUG INSERT:", test_insert)

    print("FINITO.")

if __name__ == "__main__":
    main()
