import json
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
expected = set()
for athlete in items:
    path = (root / athlete["file"]).resolve()
    check(path.is_relative_to(root), "Percorso atleta non valido")
    detail = json.loads(path.read_text(encoding="utf-8"))
    check(detail["id"] == athlete["id"], "ID incoerente")
    check(len(detail["results"]) == detail["count"] == athlete["count"], "Conteggio atleta incoerente")
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
print("API e indice ricerca validati:", meta, flush=True)
