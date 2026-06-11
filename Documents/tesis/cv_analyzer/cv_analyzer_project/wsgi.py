"""
WSGI config for cv_analyzer_project project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cv_analyzer_project.settings')

application = get_wsgi_application()
