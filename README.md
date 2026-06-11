# TalentScan IA

Sistema Django para analisis inteligente de CVs, matching contra puestos, pipeline de seleccion, roles, auditoria y reportes compartibles.

## Deploy gratis en Render

Este repositorio incluye `render.yaml` en la raiz para crear:

- Web service `talentscan-ia`
- Postgres `talentscan-db`
- HTTPS automatico
- `DEBUG=False`
- Migraciones automaticas
- `collectstatic`
- Gunicorn

Pasos:

1. En Render, crear `New > Blueprint`.
2. Conectar este repo: `Tricciardone/Tesis`.
3. Render detecta `render.yaml`.
4. Confirmar el deploy.
5. Crear admin desde Shell:

```bash
python manage.py createsuperuser
```

App:

```text
Documents/tesis/cv_analyzer
```

Guia extendida:

```text
Documents/tesis/cv_analyzer/deploy/RENDER_FREE.md
```
