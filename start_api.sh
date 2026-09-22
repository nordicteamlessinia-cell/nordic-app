#!/bin/sh
set -eu

if [ -n "${COCKROACH_CA_URL:-}" ]; then
  mkdir -p "$HOME/.postgresql"
  python - <<'PY'
import os
import pathlib
import urllib.request

url = os.environ["COCKROACH_CA_URL"]
path = pathlib.Path.home() / ".postgresql" / "root.crt"
urllib.request.urlretrieve(url, path)
path.chmod(0o600)
print(f"CockroachDB CA installata in {path}")
PY
fi

exec python -m uvicorn api_nordic:app \
  --host 0.0.0.0 \
  --port "${PORT:-8080}"
