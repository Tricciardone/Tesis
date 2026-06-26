#!/bin/bash

echo "🔧 Configurando Django..."

# Aplicar migraciones
echo "📋 Aplicando migraciones..."
python manage.py makemigrations
python manage.py migrate

# Crear superusuario si no existe
echo "👤 Configurando superusuario..."
python manage.py shell << 'EOF'
from django.contrib.auth.models import User
import os

username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"✅ Superusuario '{username}' creado exitosamente!")
    print(f"   Email: {email}")
    print(f"   Password: {password}")
else:
    print(f"✅ Superusuario '{username}' ya existe!")
EOF

# Recopilar archivos estáticos
echo "📦 Recopilando archivos estáticos..."
python manage.py collectstatic --noinput

echo "✅ Django configurado correctamente!"
echo ""
echo "🌐 Accesos al sistema:"
echo "   - Aplicación: http://localhost:8000"
echo "   - Admin: http://localhost:8000/admin"
echo "   - Usuario admin: admin / admin123"
echo ""
