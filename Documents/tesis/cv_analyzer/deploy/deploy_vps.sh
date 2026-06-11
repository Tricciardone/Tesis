#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/talentscan}"
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.production"

cd "${APP_DIR}"

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "Falta ${APP_DIR}/${ENV_FILE}. Copia .env.production.example y completa dominio/secretos."
  exit 1
fi

mkdir -p backups

if docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" ps postgres >/dev/null 2>&1; then
  BACKUP_FILE="backups/postgres-$(date +%Y%m%d-%H%M%S).sql"
  echo "Generando backup previo en ${BACKUP_FILE}"
  docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" exec -T postgres \
    sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > "${BACKUP_FILE}" || true
fi

docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" pull || true
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" up -d --build
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE_FILE}" ps

echo "Deploy finalizado."
