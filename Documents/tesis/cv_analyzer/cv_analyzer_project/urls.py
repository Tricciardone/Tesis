"""
URL configuration for cv_analyzer_project project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.views.generic import RedirectView


def healthz(request):
    return JsonResponse({'status': 'ok'})

urlpatterns = [
    path('healthz/', healthz, name='healthz'),
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='/cvs/', permanent=False)),
    path('auth/', include('authentication.urls')),
    path('cvs/', include('cvs.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
