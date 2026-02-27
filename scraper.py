import os
import time
import hashlib
import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

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

    # debug
    with open("debug_calendar.html", "w") as f:
        f.write(html)

    rows = soup.find_all("tr")     # selector più robusto
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

def fetch_race_page(url):
    if not url:
        return None
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return r.text
    except:
        return None

def parse_results(html):
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    rows = soup.find_all("tr")
    results = []

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 3:
            continue

        results.append({
            "athlete": cols[0].get_text(strip=True),
            "team": cols[1].get_text(strip=True),
            "time": cols[2].get_text(strip=True)
        })

    return results

def insert_event(event):
    existing = supabase.table("sci_eventi") \
        .select("*") \
        .eq("event_hash", event["event_hash"]) \
        .execute()

    if existing.data:
        return existing.data[0]["id"]

    res = supabase.table("sci_eventi").insert(event).execute()
    return res.data[0]["id"]

def insert_results(event_id, results):
    for r in results:
        r["event_id"] = event_id
        supabase.table("sci_risultati").insert(r).execute()

def main():
    print("SUPABASE_URL:", SUPABASE_URL)
    print("SUPABASE_KEY PRESENTE:", SUPABASE_KEY is not None)

    html = fetch_calendar_page()
    events = parse_calendar(html)

    print("EVENTI TROVATI:", len(events))

    for evt in events:
        print("Evento:", evt["date"], evt["race"])

        event_id = insert_event(evt)

        if evt["link"]:
            race_html = fetch_race_page(evt["link"])
            results = parse_results(race_html)

            if results:
                insert_results(event_id, results)
                print("  Risultati inseriti:", len(results))

        time.sleep(1)

if __name__ == "__main__":
    main()
