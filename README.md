# TalentScan IA

Sistema Django para análisis inteligente de CVs, matching contra puestos,
pipeline de selección, roles, auditoría y reportes compartibles.

## Estructura

La aplicación principal está en:

```text
Documents/tesis/TalentScanIA
```

Componentes principales:

- `talentscan_project`: configuración Django, URLs, WSGI y ASGI.
- `cvs`: gestión de perfiles profesionales, análisis IA, matching y pipeline.
- `authentication`: registro, login y logout.
- `templates`: interfaz HTML/Bootstrap.
- `deploy`: scripts y documentación de despliegue.
- `docker-compose.yml`: entorno local con Django y PostgreSQL.
- `render.yaml`: blueprint de Render.

## Desarrollo local con Docker

```bash
cd Documents/tesis/TalentScanIA
docker compose up -d --build
docker compose exec web python manage.py migrate
```

La app queda disponible en:

```text
http://localhost:8090/
```

Health check:

```text
http://localhost:8090/healthz/
```

## Deploy gratis en Render

Este repositorio incluye `render.yaml` en la raíz para crear:

- Web service `talentscan-ia`
- Postgres `talentscan-db`
- Base de datos `talentscan`
- HTTPS automático
- `DEBUG=False`
- Migraciones automáticas
- `collectstatic`
- Gunicorn con `talentscan_project.wsgi:application`

Pasos:

1. En Render, crear `New > Blueprint`.
2. Conectar este repo: `Tricciardone/Tesis`.
3. Render detecta `render.yaml`.
4. Confirmar el deploy.
5. Configurar `OPENAI_API_KEY`.
6. Configurar `DJANGO_SUPERUSER_PASSWORD` o crear el admin desde Shell:

```bash
python manage.py createsuperuser
```

Guía extendida:

```text
Documents/tesis/TalentScanIA/deploy/RENDER_FREE.md
```
