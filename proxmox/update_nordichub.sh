#!/bin/bash
set -Eeuo pipefail
umask 077

base=/home/nordichub
source_repo="$base/nordic-app"
publish_repo="$base/nordichub-publish"
python="$base/venv/bin/python"
output="$base/static_api_test"
backups="$base/backups"

exec 9>"$base/.nordichub-update.lock"
flock -n 9 || { echo "Un aggiornamento e gia in corso"; exit 1; }

export DATABASE_URL='dbname=nordichub client_encoding=UTF8'
export PGCLIENTENCODING=UTF8 TZ=Europe/Rome PYTHONUNBUFFERED=1
export FISI_FULL_HISTORY=0 FISI_COMMITTEES=all FISI_FORCE_REFRESH=0
export FIS_FULL_HISTORY=0 FIS_ONLY_ITALIANS=0 FIS_FORCE_REFRESH=0
export FIS_MAX_RACES=0 FIS_TEST_RACE_ID=''
unset FISI_SEASONS FIS_SEASONS
export GIT_TERMINAL_PROMPT=0

cd "$publish_repo"
test "$(git branch --show-current)" = proxmox-static-api
test -z "$(git status --porcelain)"
git pull --ff-only origin proxmox-static-api

mkdir -p "$backups"
stamp=$(date +%Y%m%d_%H%M%S)
backup="$backups/nordichub_$stamp.dump"
pg_dump -Fc -d nordichub -f "$backup.partial"
pg_restore -l "$backup.partial" >/dev/null
mv "$backup.partial" "$backup"
echo "Backup salvato: $backup"

cd "$source_repo"
"$python" scraper_fisi.py
"$python" scraper_fis.py

# Versione PostgreSQL senza modificare lo script originale.
sed 's/::STRING/::TEXT/g' create_unified_view_v2.py > create_unified_view_postgres.py
"$python" create_unified_view_postgres.py

export STATIC_API_OUTPUT="$output"
"$python" export_static_api.py
"$python" "$publish_repo/proxmox/validate_local_api.py" "$output"

cd "$publish_repo"
rsync -a --delete "$output/" static_api/
git add -- static_api/
if ! git diff --cached --quiet; then
    git commit -m "Aggiorna API Nordic Hub da Proxmox $stamp"
fi
# Riprova anche un eventuale commit rimasto locale dopo un errore di rete.
git push origin proxmox-static-api

# Mantieni gli ultimi 8 backup completi; i CSV originali non vengono toccati.
"$python" - <<'PY'
from pathlib import Path
import re
folder = Path("/home/nordichub/backups")
backups = sorted(p for p in folder.iterdir()
                 if p.is_file() and re.fullmatch(r"nordichub_\d{8}_\d{6}\.dump", p.name))
for path in backups[:-8]:
    path.unlink()
PY

echo "Aggiornamento locale e invio a GitHub completati."
