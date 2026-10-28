#!/bin/bash
set -Eeuo pipefail
test "$(id -u)" -eq 0 || { echo "Eseguire come root nel contenitore 103"; exit 1; }

base=/home/nordichub
repo="$base/nordichub-publish"
test -f "$base/nordic-app/db.py"
test -x "$base/venv/bin/python"
test -f "$base/.ssh/nordichub_github"
test -f "$repo/proxmox/update_nordichub.sh"
test -f "$repo/proxmox/validate_local_api.py"
command -v flock >/dev/null
command -v rsync >/dev/null
command -v pg_dump >/dev/null
command -v pg_restore >/dev/null

install -d -m 700 -o nordichub -g nordichub "$base/bin" "$base/backups"
install -m 700 -o nordichub -g nordichub "$repo/proxmox/update_nordichub.sh" "$base/bin/update_nordichub.sh"

cat > /etc/systemd/system/nordichub-update.service <<'UNIT'
[Unit]
Description=Aggiornamento locale risultati Nordic Hub e invio API a GitHub
Wants=network-online.target
After=network-online.target postgresql.service
Requires=postgresql.service

[Service]
Type=oneshot
User=nordichub
Group=nordichub
WorkingDirectory=/home/nordichub/nordic-app
Environment=HOME=/home/nordichub
Environment=TZ=Europe/Rome
Environment=PYTHONUNBUFFERED=1
UMask=0077
Nice=10
TimeoutStartSec=5h
ExecStart=/bin/bash /home/nordichub/bin/update_nordichub.sh
UNIT

cat > /etc/systemd/system/nordichub-update.timer <<'UNIT'
[Unit]
Description=Nordic Hub lunedi e martedi alle 12 ora italiana

[Timer]
OnCalendar=Mon,Tue *-*-* 12:00:00 Europe/Rome
AccuracySec=1s
RandomizedDelaySec=0
Persistent=false
Unit=nordichub-update.service

[Install]
WantedBy=timers.target
UNIT

systemd-analyze verify /etc/systemd/system/nordichub-update.service /etc/systemd/system/nordichub-update.timer
systemctl daemon-reload
systemctl enable --now nordichub-update.timer
systemctl list-timers --all nordichub-update.timer --no-pager
echo "Timer installato. Il test manuale va avviato con systemctl start --no-block nordichub-update.service"
