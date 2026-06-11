"""
ASGI config for cv_analyzer_project project.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cv_analyzer_project.settings')

application = get_asgi_application()
