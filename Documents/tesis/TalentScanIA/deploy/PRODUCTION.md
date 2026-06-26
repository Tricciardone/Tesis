# Despliegue seguro de TalentScan IA

Esta guía publica el sistema en un VPS Linux con Docker, HTTPS automático y tráfico directo bloqueado.

## 1. DNS

Apuntá un registro `A` del dominio al IP público del servidor:

```text
talentscan.example.com -> IP_DEL_SERVIDOR
```

## 2. Preparar el servidor

Instalá Docker y Docker Compose Plugin. En Ubuntu:

```bash
sudo apt update
sudo apt install -y ca-certificates curl ufw
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```

O ejecutá el bootstrap incluido:

```bash
sudo bash deploy/bootstrap_vps.sh
```

Cerrá todo salvo SSH, HTTP y HTTPS:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw status verbose
```

## 3. Variables de producción

Copiá el ejemplo:

```bash
cp .env.production.example .env.production
```

Editá `.env.production`:

```bash
nano .env.production
```

Valores obligatorios:

```text
APP_DOMAIN=tu-dominio.com
ACME_EMAIL=tu-email@dominio.com
DEBUG=False
SECRET_KEY=una-clave-larga-y-random
ALLOWED_HOSTS=tu-dominio.com
CSRF_TRUSTED_ORIGINS=https://tu-dominio.com
DB_PASSWORD=otra-clave-larga-y-random
ALLOW_PUBLIC_REGISTRATION=False
```

Generar una `SECRET_KEY`:

```bash
python - <<'PY'
from secrets import token_urlsafe
print(token_urlsafe(64))
PY
```

## 4. Levantar producción

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

También podés usar el script incluido:

```bash
chmod +x deploy/deploy_vps.sh
./deploy/deploy_vps.sh
```

Caddy obtiene el certificado TLS automáticamente. Si falla, revisá que el dominio apunte al servidor y que los puertos 80/443 estén abiertos.

## 5. Crear usuario admin

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml exec web python manage.py createsuperuser
```

Entrá por:

```text
https://tu-dominio.com/auth/login/
```

## 6. Operación segura

Ver logs:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f web
docker compose --env-file .env.production -f docker-compose.prod.yml logs -f caddy
```

Actualizar:

```bash
git pull
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
```

Backup de base de datos:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml exec postgres sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > backup.sql
```

## 7. Deploy automático desde GitHub Actions

El workflow está en:

```text
.github/workflows/deploy-vps.yml
```

Configurá estos secretos en GitHub:

```text
VPS_HOST=IP_DEL_SERVIDOR
VPS_USER=usuario_ssh
VPS_SSH_KEY=clave_privada_ssh
```

En el VPS debe existir `/opt/talentscan/.env.production` con las variables reales. El workflow sube el código y ejecuta `deploy/deploy_vps.sh`.

## Seguridad aplicada

- Solo Caddy expone puertos públicos `80/443`.
- Django y Postgres quedan en red interna de Docker.
- Postgres no publica `5432`.
- HTTPS automático.
- `DEBUG=False`.
- `ALLOWED_HOSTS` cerrado.
- CSRF restringido al dominio.
- CORS cerrado por defecto.
- Cookies seguras.
- HSTS activo.
- Registro público deshabilitado por defecto.
- PDFs servidos por vista autenticada, no como `/media/` público.
