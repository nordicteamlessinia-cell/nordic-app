import datetime
import os
import re
import time

import requests
from bs4 import BeautifulSoup

from db import fis_race_has_results, upsert_risultati_fis


SAVE_ONLY_ITALIANS = os.getenv("FIS_ONLY_ITALIANS", "0") == "1"
FORCE_REFRESH = os.getenv("FIS_FORCE_REFRESH", "0") == "1"
MAX_RACES = int(os.getenv("FIS_MAX_RACES", "0") or "0")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) NordicHub/GitHubActions"
}


def current_fis_season():
    now = datetime.datetime.now()
    return now.year + 1 if now.month >= 7 else now.year


def seasons_to_scan():
    explicit = os.getenv("FIS_SEASONS", "").strip()
    if explicit:
        return [int(x.strip()) for x in explicit.split(",") if x.strip()]

    current = current_fis_season()
    if os.getenv("FIS_FULL_HISTORY", "0") == "1":
        start = int(os.getenv("FIS_START_SEASON", "2010"))
        return list(range(start, current + 1))

    return [current]


def season_months(season):
    previous = season - 1
    return [
        f"10-{previous}", f"11-{previous}", f"12-{previous}",
        f"01-{season}", f"02-{season}", f"03-{season}", f"04-{season}",
    ]


def format_fis_date(text):
    if not text or text == "N/D":
        return "N/D"

    clean = text.split("\n")[0].strip()
    for fmt in ("%B %d, %Y", "%d %b %Y", "%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(clean, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return clean


def fetch_events(season):
    print(f"🌍 FIS: scansione stagione {season}", flush=True)
    event_ids = []

    for month in season_months(season):
        url = (
            "https://www.fis-ski.com/DB/cross-country/calendar-results.html"
            f"?eventselection=&place=&sectorcode=CC&seasoncode={season}&categorycode="
            "&disciplinecode=&gendercode=&racedate=&racecodex=&nationcode="
            f"&seasonmonth={month}&saveselection=-1&seasonselection="
            "&include_at_least_one_results=true"
        )
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            for event_id in re.findall(r"eventid=(\d+)", response.text, re.IGNORECASE):
                if event_id not in event_ids:
                    event_ids.append(event_id)
        except Exception as exc:
            print(f"⚠️ FIS mese {month}: {exc}", flush=True)
        time.sleep(0.4)

    print(f"   Trovati {len(event_ids)} eventi FIS", flush=True)
    return event_ids


def fetch_races(event_id):
    url = f"https://www.fis-ski.com/DB/general/event-details.html?sectorcode=CC&eventid={event_id}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        return list(dict.fromkeys(re.findall(r"raceid=(\d+)", response.text, re.IGNORECASE)))
    except Exception as exc:
        print(f"⚠️ Evento FIS {event_id}: {exc}", flush=True)
        return []


def scrape_race(race_id):
    if not FORCE_REFRESH and fis_race_has_results(race_id):
        return 0

    url = f"https://www.fis-ski.com/DB/general/results.html?sectorcode=CC&raceid={race_id}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except Exception as exc:
        print(f"⚠️ Gara FIS {race_id}: {exc}", flush=True)
        return 0

    soup = BeautifulSoup(response.text, "html.parser")

    place_node = soup.select_one(".event-header__name h1")
    date_node = soup.select_one(".date__full")
    category_node = soup.select_one(".event-header__kind")
    speciality_node = soup.select_one(".event-header__subtitle")

    place = place_node.text.strip() if place_node else "N/D"
    race_date = format_fis_date(date_node.text.strip() if date_node else "N/D")
    category = category_node.text.strip() if category_node else "FIS"
    speciality = speciality_node.text.strip() if speciality_node else "Cross-Country"
    race_name = f"{place} - {speciality}" if speciality and speciality != "N/D" else place

    athlete_rows = soup.find_all("a", class_="table-row")
    if not athlete_rows:
        print(f"   ⚠️ FIS race {race_id}: nessuna riga risultati trovata", flush=True)
        return 0

    results = []
    for row in athlete_rows:
        try:
            name_node = row.find("div", class_="athlete-name")
            name = name_node.text.strip() if name_node else "N/D"
            if name == "N/D":
                continue

            nation_node = row.find("span", class_="country__name-short")
            nation = nation_node.text.strip() if nation_node else "N/D"
            if SAVE_ONLY_ITALIANS and nation != "ITA":
                continue

            columns = [col.text.strip() for col in row.find_all("div") if col.text.strip()]
            position = columns[0] if len(columns) > 0 else "N/D"
            fis_code = columns[1] if len(columns) > 1 else ""
            result_time = columns[-2] if len(columns) > 2 else "N/D"
            fis_points = columns[-1] if len(columns) > 2 else ""

            results.append({
                "id_gara_fis": str(race_id),
                "atleta_nome": name,
                "codice_fis": fis_code,
                "nazione": nation,
                "societa": "N/D",
                "comitato": "FIS",
                "categoria": category,
                "specialita": speciality,
                "posizione": position,
                "tempo": result_time,
                "punti_fis": fis_points,
                "gara_nome": race_name,
                "luogo": place,
                "data_gara": race_date,
            })
        except Exception:
            continue

    if not results:
        return 0

    saved = upsert_risultati_fis(results)
    print(f"   ✅ FIS race {race_id}: {saved} risultati | {race_name}", flush=True)
    return saved


def main():
    print("=========================================")
    print("❄️ NORDIC HUB - SCRAPER FIS / COCKROACHDB")
    print("=========================================")

    total = 0
    races_attempted = 0

    for season in seasons_to_scan():
        for event_id in fetch_events(season):
            for race_id in fetch_races(event_id):
                total += scrape_race(race_id)
                races_attempted += 1

                if MAX_RACES and races_attempted >= MAX_RACES:
                    print(
                        f"🧪 Limite test raggiunto: {races_attempted} gare FIS esaminate",
                        flush=True,
                    )
                    print(f"🏁 Scraper FIS completato: {total} risultati elaborati", flush=True)
                    return

                time.sleep(0.25)
            time.sleep(0.3)

    print(f"🏁 Scraper FIS completato: {total} risultati elaborati", flush=True)


if __name__ == "__main__":
    main()
