# Deploy gratis en Render

Render permite crear una app web gratis y una base Postgres gratis para proyectos de prueba/hobby. No lo tomes como producción crítica: el free tier puede tener límites, dormir por inactividad o restricciones de uso.

## 1. Subir el código a GitHub

El deploy de Render sale desde un repo GitHub. Este proyecto ya tiene:

```text
render.yaml
deploy/render_build.sh
deploy/render_start.sh
```

## 2. Crear Blueprint en Render

1. Entrá a Render.
2. New > Blueprint.
3. Conectá el repo de GitHub.
4. Elegí este repositorio.
5. Render detecta `render.yaml`.
6. Confirmá la creación de:
   - `talentscan-ia`
   - `talentscan-db`

## 3. Variables

El Blueprint ya configura:

```text
DEBUG=False
SECRET_KEY=generada por Render
DATABASE_URL=desde talentscan-db
ALLOWED_HOSTS=.onrender.com
CSRF_TRUSTED_ORIGINS=https://*.onrender.com
ALLOW_PUBLIC_REGISTRATION=False
```

Si vas a usar OpenAI, agregá manualmente:

```text
OPENAI_API_KEY=tu_api_key
```

## 4. Crear admin sin Shell

Render Free no incluye Shell. Para crear el admin:

1. Abrí el servicio `talentscan-ia`.
2. Environment.
3. Agregá o editá:

```text
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=tu-email@example.com
DJANGO_SUPERUSER_PASSWORD=una-clave-segura
```

4. Manual Deploy > Deploy latest commit.
5. Al arrancar, el sistema crea o actualiza ese superusuario automáticamente.

Después entrás en:

```text
https://talentscan-ia.onrender.com/auth/login/
```

## Limitación importante de free hosting

Los archivos PDF cargados localmente pueden no ser persistentes en servicios gratuitos si el contenedor se reconstruye. La base de datos sí queda en Postgres, pero para archivos sensibles y persistentes conviene luego sumar almacenamiento privado tipo S3/R2/Supabase Storage.

Para una demo pública de tesis funciona. Para uso real con CVs, pasar a almacenamiento privado persistente es el siguiente paso.
