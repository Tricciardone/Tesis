# Deploy gratis en Render

Render permite crear una app web gratis y una base Postgres gratis para proyectos de prueba/hobby. No debe tomarse como produccion critica: el free tier puede tener limites, dormir por inactividad o restricciones de uso.

## 1. Subir el codigo a GitHub

El deploy de Render sale desde un repo GitHub. Este proyecto tiene:

```text
render.yaml
deploy/render_build.sh
deploy/render_start.sh
```

## 2. Crear Blueprint en Render

1. Entrar a Render.
2. New > Blueprint.
3. Conectar el repo de GitHub.
4. Elegir este repositorio.
5. Render detecta `render.yaml`.
6. Confirmar la creacion de:
   - `talentscan-ia`
   - `talentscan-ia-develop`
   - `talentscan-db`
   - `talentscan-db-develop`

## 3. Ambientes y ramas

El Blueprint define dos servicios web separados:

```text
Produccion:
- Servicio: talentscan-ia
- Branch: master
- Base: talentscan-db
- Database name: talentscan

Desarrollo/testing:
- Servicio: talentscan-ia-develop
- Branch: develop
- Base: talentscan-db-develop
- Database name: talentscan_develop
```

Cada servicio debe usar su propia `DATABASE_URL`. No mezcles datos de prueba con la base productiva.

## 4. Variables

El Blueprint configura:

```text
DEBUG=False
SECRET_KEY=generada por Render
DATABASE_URL=desde la base correspondiente
ALLOWED_HOSTS=.onrender.com
CSRF_TRUSTED_ORIGINS=https://*.onrender.com
DJANGO_SETTINGS_MODULE=talentscan_project.settings
ALLOW_PUBLIC_REGISTRATION=False
```

Configurar manualmente en cada servicio:

```text
OPENAI_API_KEY=tu_api_key
DJANGO_SUPERUSER_PASSWORD=una-clave-segura
```

## 5. Crear admin sin Shell

Render Free no incluye Shell. Para crear el admin:

1. Abrir el servicio correspondiente (`talentscan-ia` o `talentscan-ia-develop`).
2. Environment.
3. Agregar o editar:

```text
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=tu-email@example.com
DJANGO_SUPERUSER_PASSWORD=una-clave-segura
```

4. Manual Deploy > Deploy latest commit.
5. Al arrancar, el sistema crea o actualiza ese superusuario automaticamente.

URLs esperadas:

```text
https://talentscan-ia.onrender.com/auth/login/
https://talentscan-ia-develop.onrender.com/auth/login/
```

## 6. Limitacion importante de free hosting

Los archivos PDF cargados localmente pueden no ser persistentes en servicios gratuitos si el contenedor se reconstruye. La base de datos queda en Postgres, pero para archivos sensibles y persistentes conviene sumar almacenamiento privado tipo S3/R2/Supabase Storage.

Para una demo publica de tesis funciona. Para uso real con CVs, pasar a almacenamiento privado persistente es el siguiente paso.
