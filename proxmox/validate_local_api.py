import json
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

expected_rosters = {}
athletes_by_id = {a["id"]: a for a in items}
expected = set()
for athlete in items:
    path = (root / athlete["file"]).resolve()
    check(path.is_relative_to(root), "Percorso atleta non valido")
    detail = json.loads(path.read_text(encoding="utf-8"))
    check(detail["id"] == athlete["id"], "ID incoerente")
    check(len(detail["results"]) == detail["count"] == athlete["count"], "Conteggio atleta incoerente")
    for row in detail["results"]:
        club_name = clean_text(row.get("societa"))
        if not club_name:
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
        check(isinstance(item[field], list) and all(isinstance(v, str) for v in item[field]),
              f"Campo {field} non valido")
        check(set(item[field]) == expected_values and len(item[field]) == len(expected_values),
              f"Campo {field} incoerente")
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
    club_files.add(path)
check(actual_rosters == set(expected_rosters), "Atleti o stagioni mancanti nell'indice societa")
check(club_files == {p.resolve() for p in (root / "v1/clubs/data").glob("*.json")}, "File societa aggiuntivi o mancanti")
print("API, indice gare e atleti delle societa validati:", meta, flush=True)
