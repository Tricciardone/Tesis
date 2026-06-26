#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Ejecuta este script con sudo."
  exit 1
fi

apt-get update
apt-get install -y ca-certificates curl ufw git rsync

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi

ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

mkdir -p /opt/talentscan
chown -R "${SUDO_USER:-$USER}:${SUDO_USER:-$USER}" /opt/talentscan

echo "Servidor listo. Copia el proyecto a /opt/talentscan y ejecuta deploy/deploy_vps.sh."
