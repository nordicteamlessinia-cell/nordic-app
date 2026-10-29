import json
import re
from datetime import date, datetime
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
meta = json.loads((root / "v1/meta.json").read_text(encoding="utf-8"))
index = json.loads((root / "v1/athletes/index.json").read_text(encoding="utf-8"))
items = index["items"]

def check(condition, message):
    if not condition:
        raise SystemExit(message)

check(meta["athletes"] >= 12000, "Troppo pochi profili")
check(meta["results"] >= 199110, "Risultati sotto la copia verificata")
check(meta["races"] >= 9351, "Gare sotto la copia verificata")
check(len(items) == index["count"] == meta["athletes"], "Conteggio profili incoerente")
check(len({a["id"] for a in items}) == len(items), "ID atleta duplicati")
check(sum(a["count"] for a in items) == meta["results"], "Totale risultati incoerente")
def clean_text(value):
    value = str(value or "").strip()
    return "" if value.upper() in ("", "-", "N/D", "NONE", "NULL") else value

def valid_club(value):
    text = clean_text(value)
    return (bool(text) and text.upper() not in {"DNS", "DNF", "DSQ", "DQ", "NPS", "LAP", "NP", "RIT"}
            and re.fullmatch(r'''[0-9\s:.,+\-/'"’′″;()]+''', text) is None)

def result_day(row):
    for field in ("data_gara_iso", "data_gara"):
        value = clean_text(row.get(field))
        if not value:
            continue
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            pass
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                pass
    return None

# Verifica indipendente delle aggregazioni usando le righe originali.
def filter_keys(row):
    day = result_day(row)
    if day:
        first = day.year - (day.month < 9)
        periods = {"Tutte", str(day.year), f"{first}/{first + 1}"}
    else:
        periods = {"Tutte", "Senza data"}
    committees = {"Tutti", clean_text(row.get("comitato")) or "Non indicato"}
    return {json.dumps([p, c], ensure_ascii=False, separators=(",", ":"))
            for p in periods for c in committees}

expected_stats = {}
expected_facets = {}
def stat_cell(key):
    return expected_stats.setdefault(key, {"athletes": set(), "results": 0, "races": set()})

expected_rosters = {}
expected_excluded = {}
athletes_by_id = {a["id"]: a for a in items}
expected = set()
for athlete in items:
    path = (root / athlete["file"]).resolve()
    check(path.is_relative_to(root), "Percorso atleta non valido")
    detail = json.loads(path.read_text(encoding="utf-8"))
    check(detail["id"] == athlete["id"], "ID incoerente")
    check(len(detail["results"]) == detail["count"] == athlete["count"], "Conteggio atleta incoerente")
    stat_cell('["Tutte","Tutti"]')["athletes"].add(athlete["id"])
    for row in detail["results"]:
        for key in filter_keys(row):
            data = stat_cell(key)
            data["athletes"].add(athlete["id"])
            data["results"] += 1
            name = clean_text(row.get("societa"))
            if valid_club(name):
                members = expected_facets.setdefault(name, {}).setdefault(key, {})
                member = members.setdefault(athlete["id"], {"results_count": 0, "last_date": ""})
                member["results_count"] += 1
                day = result_day(row)
                if day:
                    member["last_date"] = max(member["last_date"], day.isoformat())
        club_name = clean_text(row.get("societa"))
        if not club_name:
            continue
        if not valid_club(club_name):
            expected_excluded[club_name] = expected_excluded.get(club_name, 0) + 1
            continue
        day = result_day(row)
        start = (day.year if day.month >= 9 else day.year - 1) if day else None
        season = f"{start}/{start + 1}" if day else "Senza data"
        key = (club_name, season, athlete["id"])
        data = expected_rosters.setdefault(key, {"count": 0, "dates": [], "origins": set()})
        data["count"] += 1
        if day:
            data["dates"].append(day.isoformat())
        if clean_text(row.get("origine")):
            data["origins"].add(clean_text(row["origine"]))
    expected.add(path)
check(expected == {p.resolve() for p in (root / "v1/athletes/data").rglob("*.json")},
      "File atleta aggiuntivi o mancanti")
index_path = root / "v1/races/index.json"
races = [p for p in (root / "v1/races").rglob("*.json") if p != index_path]
check(len(races) == meta["races"], "Conteggio file gara incoerente")
for path in races:
    race = json.loads(path.read_text(encoding="utf-8"))
    check(len(race["items"]) == race["count"], "Conteggio classifica incoerente")
race_index = json.loads(index_path.read_text(encoding="utf-8"))
indexed = race_index["items"]
check(len(indexed) == race_index["count"] == meta["races"], "Conteggio indice gare incoerente")
check(race_index["generated_at"] == meta["generated_at"], "Indice gare non aggiornato")
paths = set()
for item in indexed:
    origin = item.get("origine")
    race_id = item.get("id_gara")
    check(origin in ("FIS", "FISI") and isinstance(race_id, str) and race_id,
          "Fonte o ID non valido nell'indice gare")
    path = (root / item["file"]).resolve()
    check(path.is_relative_to((root / "v1/races").resolve()), "Percorso gara non valido")
    check(path == (root / "v1/races" / origin.lower() / f"{race_id}.json").resolve(),
          "Percorso gara incoerente")
    check(path not in paths, "Gara duplicata nell'indice")
    check(path.is_file(), "Classifica indicizzata mancante")
    detail = json.loads(path.read_text(encoding="utf-8"))
    check(detail["origin"] == origin and detail["race_id"] == race_id, "Identita gara incoerente")
    check(item["results_count"] == detail["count"], "Numero risultati gara incoerente")
    for field, source_field in (("societa", "societa"), ("categorie", "categoria")):
        def clean(value):
            text = str(value or "").strip()
            return "" if text.upper() in ("", "-", "N/D", "NONE", "NULL") else text
        expected_values = {clean(row.get(source_field)) for row in detail["items"]} - {""}
        if field == "societa":
            expected_values = {value for value in expected_values if valid_club(value)}
        check(isinstance(item[field], list) and all(isinstance(v, str) for v in item[field]),
              f"Campo {field} non valido")
        check(set(item[field]) == expected_values and len(item[field]) == len(expected_values),
              f"Campo {field} incoerente")
    keys = set().union(*(filter_keys(row) for row in detail["items"]))
    check(sorted(keys) == item.get("filter_keys"), "Filtri gara incoerenti")
    for key in keys:
        stat_cell(key)["races"].add((origin, race_id))
    paths.add(path)
check(paths == {p.resolve() for p in races}, "Indice gare incompleto o con file aggiuntivi")
clubs = json.loads((root / "v1/clubs/index.json").read_text(encoding="utf-8"))
check(clubs["count"] == len(clubs["items"]), "Conteggio societa incoerente")
check(clubs["generated_at"] == meta["generated_at"], "Indice societa non aggiornato")
check(len({club["id"] for club in clubs["items"]}) == clubs["count"], "ID societa duplicati")
actual_rosters = set()
club_files = set()
club_names = set()
for club in clubs["items"]:
    check(valid_club(club["name"]), "Nome societa numerico, tempo o segnaposto")
    check(club["name"] not in club_names, "Societa duplicata")
    club_names.add(club["name"])
    path = (root / club["file"]).resolve()
    check(path.is_relative_to((root / "v1/clubs/data").resolve()), "Percorso societa non valido")
    check(path.name == f"{club['id']}.json" and path not in club_files, "File societa incoerente")
    detail = json.loads(path.read_text(encoding="utf-8"))
    check(detail["id"] == club["id"] and detail["name"] == club["name"], "Identita societa incoerente")
    check(detail["generated_at"] == meta["generated_at"], "Dettaglio societa non aggiornato")
    check(set(detail["seasons"]) == set(club["seasons"]), "Stagioni societa incoerenti")
    total = 0
    for season, members in detail["seasons"].items():
        check(len(members) == club["seasons"][season], "Totale atleti stagione incoerente")
        for member in members:
            key = (club["name"], season, member["id"])
            check(key not in actual_rosters and key in expected_rosters, "Atleta societa duplicato o non osservato")
            actual_rosters.add(key)
            expected_member = expected_rosters[key]
            check(member["results_count"] == expected_member["count"], "Risultati societa/atleta incoerenti")
            check(set(member["origins"]) == expected_member["origins"], "Fonti societa/atleta incoerenti")
            dates = expected_member["dates"]
            check(member["first_date"] == (min(dates) if dates else "") and
                  member["last_date"] == (max(dates) if dates else ""), "Date societa/atleta incoerenti")
            athlete = athletes_by_id[member["id"]]
            for field in ("name", "file", "birth_year", "fis_code", "fisi_code", "count"):
                check(member.get(field) == athlete.get(field), "Profilo societa/atleta incoerente")
            total += member["results_count"]
    check(total == club["results_count"], "Totale risultati societa incoerente")
    facets = detail.get("filter_members", {})
    wanted = expected_facets[club["name"]]
    check(set(facets) == set(wanted), "Periodi/comitati societa mancanti")
    check(club.get("filter_counts") == {key: len(members) for key, members in wanted.items()},
          "Conteggi filtrati societa incoerenti")
    for key, members in facets.items():
        check(len(members) == len(wanted[key]) and {m["id"] for m in members} == set(wanted[key]),
              "Atleti filtrati duplicati o mancanti")
        for member in members:
            expected_member = wanted[key][member["id"]]
            check(all(member[k] == expected_member[k] for k in ("results_count", "last_date")),
                  "Risultati filtrati atleta incoerenti")
            athlete = athletes_by_id[member["id"]]
            check(all(member.get(k) == athlete.get(k) for k in
                      ("name", "file", "birth_year", "fis_code", "fisi_code", "count")),
                  "Identita atleta filtrato incoerente")
    club_files.add(path)
check(actual_rosters == set(expected_rosters), "Atleti o stagioni mancanti nell'indice societa")
check(club_files == {p.resolve() for p in (root / "v1/clubs/data").glob("*.json")}, "File societa aggiuntivi o mancanti")
audit = json.loads((root / "v1/clubs/excluded.json").read_text(encoding="utf-8"))
check(audit["generated_at"] == meta["generated_at"], "Elenco esclusioni non aggiornato")
check(audit["count"] == len(audit["items"]) == len(expected_excluded), "Conteggio esclusioni incoerente")
check({item["value"]: item["results_count"] for item in audit["items"]} == expected_excluded,
      "Elenco esclusioni incoerente")
check(clubs["excluded_values"] == len(expected_excluded) and
      clubs["excluded_results_count"] == sum(expected_excluded.values()), "Totale esclusioni incoerente")
statistics = json.loads((root / "v1/statistics.json").read_text(encoding="utf-8"))
check(statistics["generated_at"] == meta["generated_at"], "Statistiche non aggiornate")
expected_counts = {key: {"athletes": len(v["athletes"]), "results": v["results"], "races": len(v["races"])}
                   for key, v in expected_stats.items()}
check(statistics["cells"] == expected_counts, "Statistiche filtrate incoerenti")
check(statistics["cells"]['["Tutte","Tutti"]'] == {k: meta[k] for k in ("athletes", "results", "races")},
      "Statistiche globali incoerenti")
print("API, indice gare e atleti delle societa validati:", meta, flush=True)
