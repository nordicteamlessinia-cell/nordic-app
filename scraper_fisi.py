import datetime
import os
import re
import time
from collections import defaultdict

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from db import fisi_race_has_results, upsert_gare, upsert_risultati_fisi


BASE_URL_AJAX = "https://comitati.fisi.org/wp-admin/admin-ajax.php"

COMITATI_FISI = {
    "trentino": "Trentino (TN)",
    "alto-adige": "Alto Adige (AA)",
    "veneto": "Veneto (VE)",
    "alpi-centrali": "Alpi Centrali (AC)",
    "alpi-occidentali": "Alpi Occidentali (AOC)",
    "friuli-venezia-giulia": "Friuli Venezia Giulia (FVG)",
    "appennino-emiliano": "Appennino Emiliano (CAE)",
    "appennino-toscano": "Appennino Toscano (CAT)",
    "abruzzo": "Abruzzo (CAB)",
    "lazio-sardegna": "Lazio e Sardegna (CLS)",
    "umbro-marchigiano": "Umbro Marchigiano (CUM)",
    "campano": "Campano (CAM)",
    "calabro-lucano": "Calabro Lucano (CAL)",
    "pugliese": "Pugliese (PUG)",
    "siculo": "Siculo (SIC)",
    "ligure": "Ligure (LIG)",
    "asiva": "Valdostano (ASIVA)",
}
COMITATI_FISI_REVERSE = {v: k for k, v in COMITATI_FISI.items()}

MAPPA_NOMI_COMITATI = {
    "TRENTINO": "Trentino (TN)", "TN": "Trentino (TN)",
    "ALTO ADIGE": "Alto Adige (AA)", "AA": "Alto Adige (AA)", "SUDTIROL": "Alto Adige (AA)", "BZ": "Alto Adige (AA)",
    "VENETO": "Veneto (VE)", "VE": "Veneto (VE)",
    "ALPI CENTRALI": "Alpi Centrali (AC)", "AC": "Alpi Centrali (AC)",
    "ALPI OCCIDENTALI": "Alpi Occidentali (AOC)", "AOC": "Alpi Occidentali (AOC)",
    "VALDOSTANO": "Valdostano (ASIVA)", "ASIVA": "Valdostano (ASIVA)", "VDA": "Valdostano (ASIVA)",
    "FRIULI VENEZIA GIULIA": "Friuli Venezia Giulia (FVG)", "FVG": "Friuli Venezia Giulia (FVG)",
    "APPENNINO EMILIANO": "Appennino Emiliano (CAE)", "CAE": "Appennino Emiliano (CAE)",
    "APPENNINO TOSCANO": "Appennino Toscano (CAT)", "CAT": "Appennino Toscano (CAT)",
    "ABRUZZO": "Abruzzo (CAB)", "CAB": "Abruzzo (CAB)",
    "LAZIO E SARDEGNA": "Lazio e Sardegna (CLS)", "CLS": "Lazio e Sardegna (CLS)",
    "LIGURE": "Ligure (LIG)", "LIG": "Ligure (LIG)",
    "UMBRO MARCHIGIANO": "Umbro Marchigiano (CUM)", "CUM": "Umbro Marchigiano (CUM)",
    "CAMPANO": "Campano (CAM)", "CAM": "Campano (CAM)",
    "CALABRO LUCANO": "Calabro Lucano (CAL)", "CAL": "Calabro Lucano (CAL)",
    "PUGLIESE": "Pugliese (PUG)", "PUG": "Pugliese (PUG)",
    "SICULO": "Siculo (SIC)", "SIC": "Siculo (SIC)",
}

MAPPA_PROVINCE = {
    "AO": "Valdostano (ASIVA)",
    "TN": "Trentino (TN)", "BZ": "Alto Adige (AA)",
    "BL": "Veneto (VE)", "PD": "Veneto (VE)", "RO": "Veneto (VE)", "TV": "Veneto (VE)", "VE": "Veneto (VE)", "VR": "Veneto (VE)", "VI": "Veneto (VE)",
    "BG": "Alpi Centrali (AC)", "BS": "Alpi Centrali (AC)", "CO": "Alpi Centrali (AC)", "CR": "Alpi Centrali (AC)", "LC": "Alpi Centrali (AC)", "LO": "Alpi Centrali (AC)", "MN": "Alpi Centrali (AC)", "MI": "Alpi Centrali (AC)", "MB": "Alpi Centrali (AC)", "PV": "Alpi Centrali (AC)", "SO": "Alpi Centrali (AC)", "VA": "Alpi Centrali (AC)",
    "AL": "Alpi Occidentali (AOC)", "AT": "Alpi Occidentali (AOC)", "BI": "Alpi Occidentali (AOC)", "CN": "Alpi Occidentali (AOC)", "NO": "Alpi Occidentali (AOC)", "TO": "Alpi Occidentali (AOC)", "VB": "Alpi Occidentali (AOC)", "VC": "Alpi Occidentali (AOC)",
    "GO": "Friuli Venezia Giulia (FVG)", "PN": "Friuli Venezia Giulia (FVG)", "TS": "Friuli Venezia Giulia (FVG)", "UD": "Friuli Venezia Giulia (FVG)",
    "GE": "Ligure (LIG)", "IM": "Ligure (LIG)", "SP": "Ligure (LIG)", "SV": "Ligure (LIG)",
    "BO": "Appennino Emiliano (CAE)", "FE": "Appennino Emiliano (CAE)", "FC": "Appennino Emiliano (CAE)", "MO": "Appennino Emiliano (CAE)", "PR": "Appennino Emiliano (CAE)", "PC": "Appennino Emiliano (CAE)", "RA": "Appennino Emiliano (CAE)", "RE": "Appennino Emiliano (CAE)", "RN": "Appennino Emiliano (CAE)",
    "AR": "Appennino Toscano (CAT)", "FI": "Appennino Toscano (CAT)", "GR": "Appennino Toscano (CAT)", "LI": "Appennino Toscano (CAT)", "LU": "Appennino Toscano (CAT)", "MS": "Appennino Toscano (CAT)", "PI": "Appennino Toscano (CAT)", "PT": "Appennino Toscano (CAT)", "PO": "Appennino Toscano (CAT)", "SI": "Appennino Toscano (CAT)",
    "AQ": "Abruzzo (CAB)", "CH": "Abruzzo (CAB)", "PE": "Abruzzo (CAB)", "TE": "Abruzzo (CAB)",
    "FR": "Lazio e Sardegna (CLS)", "LT": "Lazio e Sardegna (CLS)", "RI": "Lazio e Sardegna (CLS)", "RM": "Lazio e Sardegna (CLS)", "VT": "Lazio e Sardegna (CLS)", "CA": "Lazio e Sardegna (CLS)", "NU": "Lazio e Sardegna (CLS)", "OR": "Lazio e Sardegna (CLS)", "SS": "Lazio e Sardegna (CLS)", "SU": "Lazio e Sardegna (CLS)",
    "PG": "Umbro Marchigiano (CUM)", "TR": "Umbro Marchigiano (CUM)", "AN": "Umbro Marchigiano (CUM)", "AP": "Umbro Marchigiano (CUM)", "FM": "Umbro Marchigiano (CUM)", "MC": "Umbro Marchigiano (CUM)", "PU": "Umbro Marchigiano (CUM)",
    "AV": "Campano (CAM)", "BN": "Campano (CAM)", "CE": "Campano (CAM)", "NA": "Campano (CAM)", "SA": "Campano (CAM)", "CB": "Campano (CAM)", "IS": "Campano (CAM)",
    "CZ": "Calabro Lucano (CAL)", "CS": "Calabro Lucano (CAL)", "KR": "Calabro Lucano (CAL)", "RC": "Calabro Lucano (CAL)", "VV": "Calabro Lucano (CAL)", "MT": "Calabro Lucano (CAL)", "PZ": "Calabro Lucano (CAL)",
    "BA": "Pugliese (PUG)", "BT": "Pugliese (PUG)", "BR": "Pugliese (PUG)", "FG": "Pugliese (PUG)", "LE": "Pugliese (PUG)", "TA": "Pugliese (PUG)",
    "AG": "Siculo (SIC)", "CL": "Siculo (SIC)", "CT": "Siculo (SIC)", "EN": "Siculo (SIC)", "ME": "Siculo (SIC)", "PA": "Siculo (SIC)", "RG": "Siculo (SIC)", "SR": "Siculo (SIC)", "TP": "Siculo (SIC)",
}

ACRONIMI_FISI = {
    "AA", "AC", "AOC", "CAB", "CAE", "CAL", "CAM", "CAT", "CLS", "CUM",
    "FVG", "LIG", "PUG", "SIC", "TN", "VA", "ASIVA", "VE",
    "GM1", "GM2", "GM3", "GM4", "GM5", "FFOO", "FFGG", "CSCA", "CS", "CC", "AM",
}

FONDO_KEYWORDS = ("FONDO", "SCI DI FONDO", "LANGLAUF", "CROSS COUNTRY", "NORDIC", "NORDICO", "XC")
LISTA_NERA = ("ALPINO", "SLALOM", "GIGANTE", "SUPER G", "DISCESA", "BIATHLON", "SNOWBOARD", "SKICROSS", "FREESTYLE", "ERBA", "SKIROLL", "ROLLER SKI", "ROLLERSKI", "ROLLER", "SKELETON", "BOB", "JUMP", "SALTO")

session = requests.Session()
retries = Retry(total=5, backoff_factor=2, status_forcelist=[429, 500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retries))
session.mount("http://", HTTPAdapter(max_retries=retries))
session.headers.update({"User-Agent": "Mozilla/5.0 NordicHub/GitHubActions"})


def is_cross_country(item):
    disciplina = str(item.get("disciplina", "")).upper()
    nome = str(item.get("nome", "")).upper()
    good = any(k in disciplina for k in FONDO_KEYWORDS) or any(k in nome for k in FONDO_KEYWORDS)
    bad = any(k in disciplina for k in LISTA_NERA) or any(k in nome for k in LISTA_NERA)
    return good and not bad


def detect_committee(item):
    livello = str(item.get("livello", "")).upper()
    if "WORLD" in livello or "OPA" in livello or "INTERNAZIONAL" in livello:
        return "Internazionale/FIS", 0

    c_code = str(item.get("codiceComitato", "")).strip().upper()
    c_name = str(item.get("comitato", "")).strip().upper()
    if c_code in MAPPA_NOMI_COMITATI:
        return MAPPA_NOMI_COMITATI[c_code], 1
    if c_name in MAPPA_NOMI_COMITATI:
        return MAPPA_NOMI_COMITATI[c_name], 1

    societa = str(item.get("codiceSocieta", "")).strip().upper()
    prefisso = re.match(r"^[A-Z]+", societa)
    if prefisso:
        sigla = prefisso.group(0)
        if sigla in {"AO", "VDA", "ASIVA"}:
            return "Valdostano (ASIVA)", 2
        if sigla in MAPPA_PROVINCE:
            return MAPPA_PROVINCE[sigla], 2

    nome = str(item.get("nome", "")).upper()
    luogo = str(item.get("comune", "")).upper()
    text = f"{nome} {luogo}"
    location_hints = {
        "COGNE": "Valdostano (ASIVA)", "BRUSSON": "Valdostano (ASIVA)",
        "BOSCO CHIESANUOVA": "Veneto (VE)", "ASIAGO": "Veneto (VE)", "FALCADE": "Veneto (VE)",
        "DOBBIACO": "Alto Adige (AA)", "CASIES": "Alto Adige (AA)",
        "TESERO": "Trentino (TN)", "VERMIGLIO": "Trentino (TN)",
        "SCHILPARIO": "Alpi Centrali (AC)", "LIVIGNO": "Alpi Centrali (AC)",
        "FORNI AVOLTRI": "Friuli Venezia Giulia (FVG)", "SAPPADA": "Friuli Venezia Giulia (FVG)",
        "PRAGELATO": "Alpi Occidentali (AOC)", "ROCCARASO": "Abruzzo (CAB)",
    }
    for key, committee in location_hints.items():
        if key in text:
            return committee, 3

    return "", 5


def season_from_date(data_gara):
    """FISI usa l'anno di inizio stagione: es. settembre 2026 -> idStagione 2026."""
    text = str(data_gara or "").strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            dt = datetime.datetime.strptime(text, fmt)
            return str(dt.year if dt.month >= 6 else dt.year - 1)
        except ValueError:
            continue
    now = datetime.datetime.now()
    return str(now.year if now.month >= 6 else now.year - 1)


def seasons_to_scan():
    explicit = os.getenv("FISI_SEASONS", "").strip()
    if explicit:
        return [int(x.strip()) for x in explicit.split(",") if x.strip()]

    now = datetime.datetime.now()
    current = now.year if now.month >= 6 else now.year - 1

    if os.getenv("FISI_FULL_HISTORY", "0") == "1":
        start = int(os.getenv("FISI_START_SEASON", "2010"))
        return list(range(start, current + 1))

    return [current]


def committees_to_scan():
    explicit = os.getenv("FISI_COMMITTEES", "").strip().lower()
    if not explicit:
        return list(COMITATI_FISI.items())

    wanted = {x.strip() for x in explicit.split(",") if x.strip()}
    return [(slug, name) for slug, name in COMITATI_FISI.items() if slug in wanted]


def fetch_competitions():
    seasons = seasons_to_scan()
    committees = committees_to_scan()
    print(f"🌍 FISI: scansione stagioni {seasons}", flush=True)
    print(f"   Comitati: {', '.join(slug for slug, _ in committees)}", flush=True)

    races = {}
    portal_yield = defaultdict(int)
    claims = defaultdict(list)

    for slug, portal_name in committees:
        for season in seasons:
            offset, limit = 0, 500
            while True:
                params = {
                    "action": "competizioni_get_all",
                    "idStagione": str(season),
                    "url": f"https://comitati.fisi.org/{slug}/calendario/",
                    "limit": limit,
                    "offset": offset,
                }
                try:
                    response = session.get(BASE_URL_AJAX, params=params, timeout=20)
                    response.raise_for_status()
                    data = response.json()
                except Exception as exc:
                    print(f"⚠️ {portal_name} {season}: {exc}", flush=True)
                    break

                if not isinstance(data, list) or not data:
                    break

                for item in data:
                    if not is_cross_country(item):
                        continue
                    id_comp = str(item.get("idCompetizione") or "").strip()
                    if not id_comp:
                        continue

                    portal_yield[portal_name] += 1
                    claims[id_comp].append(portal_name)
                    committee, score = detect_committee(item)

                    candidate = {
                        "id_gara_fisi": id_comp,
                        "gara_nome": item.get("nome", "Gara Senza Nome"),
                        "luogo": item.get("comune", "N/D"),
                        "data_gara": item.get("dataInizio", "N/D"),
                        "comitato": committee,
                        "disciplina": item.get("disciplina", "N/D"),
                        "codice_societa": item.get("codiceSocieta", ""),
                        "score": score,
                    }

                    current = races.get(id_comp)
                    if current is None or score < current["score"]:
                        races[id_comp] = candidate

                if len(data) < limit:
                    break
                offset += limit
            time.sleep(0.08)

    final = []
    for id_comp, race in races.items():
        if race["score"] == 5:
            race_claims = claims[id_comp]
            if race_claims:
                best_portal = min(race_claims, key=lambda name: portal_yield[name])
                race["comitato"] = best_portal if portal_yield[best_portal] <= 10000 else "Altre / Non Assegnate"
            else:
                race["comitato"] = "Altre / Non Assegnate"
        race.pop("score", None)
        final.append(race)

    saved = upsert_gare(final)
    print(f"✅ FISI: {saved} gare sincronizzate in CockroachDB", flush=True)
    return final


def extract_category_and_speciality(soup):
    texts = list(soup.stripped_strings)
    category, speciality = "", ""
    for i, text in enumerate(texts):
        upper = text.upper()
        if upper == "CATEGORIA" and i + 1 < len(texts) and texts[i + 1].upper() != "POS.":
            category = texts[i + 1]
        if "SPECIALITÀ" in upper or "SPECIALITA" in upper:
            if i + 1 < len(texts) and texts[i + 1].upper() != "CATEGORIA":
                speciality = texts[i + 1]
    combined = f"{speciality} - {category}".strip(" -") if speciality or category else "Generale"
    return combined, speciality


def scrape_race_results(race, slug, season, id_race):
    if fisi_race_has_results(id_race):
        print(f"      ℹ️ idGara {id_race}: risultati già presenti", flush=True)
        return 0

    url = f"https://comitati.fisi.org/{slug}/gara/?idGara={id_race}&idComp={race['id_gara_fisi']}&d={season}"
    response = session.get(url, timeout=25)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    category, speciality = extract_category_and_speciality(soup)
    athlete_elements = soup.find_all("span", class_="x-text-content-text-primary")
    athlete_texts = [e.get_text(strip=True) for e in athlete_elements if e.get_text(strip=True)]

    rows = []
    i = 0
    while i < len(athlete_texts) - 7:
        # Manteniamo il parser collaudato del vecchio scraper FISI.
        if athlete_texts[i].isdigit() and athlete_texts[i + 1].isdigit() and len(athlete_texts[i + 1]) >= 3:
            block = athlete_texts[i:i + 8]
            athlete_committee = "N/D"
            for value in block:
                if value.upper() in ACRONIMI_FISI:
                    athlete_committee = value.upper()
                    break

            rows.append({
                "id_gara_fisi": str(id_race),
                "id_comp_collegata": str(race["id_gara_fisi"]),
                "posizione": athlete_texts[i],
                "atleta_nome": athlete_texts[i + 2],
                "societa": athlete_texts[i + 4],
                "tempo": athlete_texts[i + 5],
                "categoria": category,
                "specialita": speciality,
                "gara_nome": race.get("gara_nome", ""),
                "luogo": race.get("luogo", "N/D"),
                "data_gara": race.get("data_gara", "N/D"),
                "comitato": athlete_committee,
            })
            i += 8
        else:
            i += 1

    if not rows:
        print(f"      ⚠️ idGara {id_race}: pagina trovata ma nessun risultato interpretato", flush=True)
        return 0

    saved = upsert_risultati_fisi(rows)
    print(f"   ✅ {race.get('gara_nome')} | {category}: {saved} risultati", flush=True)
    return saved


def parse_race_date(value):
    text = str(value or "").strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def scrape_results(races):
    total = 0
    print("⛷️ FISI: controllo classifiche", flush=True)

    future_skipped = 0

    for race in races:
        committee = race.get("comitato", "")
        if not committee or committee in {"Altre / Non Assegnate", "Internazionale/FIS"}:
            continue

        race_date = parse_race_date(race.get("data_gara"))
        if race_date and race_date > datetime.date.today():
            future_skipped += 1
            continue

        slug = COMITATI_FISI_REVERSE.get(committee)
        if not slug:
            continue

        season = season_from_date(race.get("data_gara"))
        competition_url = f"https://comitati.fisi.org/{slug}/competizione/?idComp={race['id_gara_fisi']}&d={season}"

        try:
            response = session.get(competition_url, timeout=25)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            ids = []
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if "idGara=" in href:
                    id_race = href.split("idGara=")[1].split("&")[0]
                    if id_race not in ids:
                        ids.append(id_race)

            print(
                f"   🔎 idComp {race['id_gara_fisi']} | {race.get('gara_nome', '')} | idGara trovati: {len(ids)}",
                flush=True,
            )

            if not ids:
                print(f"      ⚠️ Nessun link idGara trovato nella pagina competizione", flush=True)

            for id_race in ids:
                try:
                    total += scrape_race_results(race, slug, season, id_race)
                except Exception as exc:
                    print(f"   ⚠️ idGara {id_race}: {exc}", flush=True)
                time.sleep(0.25)
        except Exception as exc:
            print(f"⚠️ Competizione {race['id_gara_fisi']}: {exc}", flush=True)

    if future_skipped:
        print(f"⏭️ FISI: {future_skipped} competizioni future saltate", flush=True)
    print(f"✅ FISI: {total} nuovi risultati elaborati", flush=True)


def main():
    print("=========================================")
    print("❄️ NORDIC HUB - SCRAPER FISI / COCKROACHDB")
    print("=========================================")
    races = fetch_competitions()
    scrape_results(races)
    print("🏁 Scraper FISI completato")


if __name__ == "__main__":
    main()
