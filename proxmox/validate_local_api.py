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
races = list((root / "v1/races").rglob("*.json"))
check(len(races) == meta["races"], "Conteggio file gara incoerente")
for path in races:
    race = json.loads(path.read_text(encoding="utf-8"))
    check(len(race["items"]) == race["count"], "Conteggio classifica incoerente")
print("API validata:", meta, flush=True)
