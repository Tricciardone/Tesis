# TalentScan IA

Sistema Django para analisis inteligente de CVs, matching contra puestos, pipeline de seleccion, roles, auditoria y reportes compartibles.

## Estructura

La aplicacion principal esta en:

```text
Documents/tesis/TalentScanIA
```

Componentes principales:

- `talentscan_project`: configuracion Django, URLs, WSGI y ASGI.
- `cvs`: gestion de perfiles profesionales, analisis IA, matching y pipeline.
- `authentication`: registro, login y logout.
- `templates`: interfaz HTML/Bootstrap.
- `deploy`: scripts y documentacion de despliegue.
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

## Flujo de ramas

El repositorio trabaja con dos ramas principales:

- `master`: produccion estable. Debe contener solo cambios validados.
- `develop`: desarrollo y testing. Es la rama para integrar cambios antes de promoverlos.

Flujo recomendado:

```bash
git checkout develop
git pull origin develop
# trabajar y validar cambios
git push origin develop
```

Para pasar cambios validados a produccion:

```bash
git checkout master
git pull origin master
git merge develop
git push origin master
```

No se debe pushear directo a `master` salvo hotfixes controlados.

## Deploy en Render

Este repositorio incluye `render.yaml` en la raiz para crear dos ambientes independientes:

- Produccion: web service `talentscan-ia`, rama `master`, base `talentscan-db`.
- Desarrollo/testing: web service `talentscan-ia-develop`, rama `develop`, base `talentscan-db-develop`.

Ambos ambientes usan:

- Root Directory: `Documents/tesis/TalentScanIA`
- Build Command: `bash deploy/render_build.sh`
- Start Command: `bash deploy/render_start.sh`
- Health Check Path: `/healthz/`
- Gunicorn con `talentscan_project.wsgi:application`

El Blueprint tambien configura:

- Base de datos `talentscan` para produccion.
- Base de datos `talentscan_develop` para desarrollo.
- HTTPS automatico.
- `DEBUG=False`.
- Migraciones automaticas.
- `collectstatic`.

Pasos:

1. En Render, crear `New > Blueprint`.
2. Conectar este repo: `Tricciardone/Tesis`.
3. Render detecta `render.yaml`.
4. Confirmar la creacion de ambos servicios y ambas bases.
5. Configurar manualmente en cada servicio:
   - `OPENAI_API_KEY`
   - `DJANGO_SUPERUSER_PASSWORD`
6. Si el servicio ya existe en Render, verificar que apunte a la rama correcta:
   - `talentscan-ia` -> `master`
   - `talentscan-ia-develop` -> `develop`

Variables principales por ambiente:

```text
SECRET_KEY=generada por Render
DEBUG=False
DATABASE_URL=desde la base correspondiente
OPENAI_API_KEY=configurada manualmente
ALLOWED_HOSTS=.onrender.com
CSRF_TRUSTED_ORIGINS=https://*.onrender.com
DJANGO_SETTINGS_MODULE=talentscan_project.settings
```

Crear admin desde Shell si corresponde:

```bash
python manage.py createsuperuser
```

Guia extendida:

```text
Documents/tesis/TalentScanIA/deploy/RENDER_FREE.md
```
