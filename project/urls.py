"""
URL Configuration for Smart Campus Token Management System
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic.base import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from apps.authentication.views import LoginPageView
from apps.core.views import api_home

urlpatterns = [
    path('', RedirectView.as_view(url='/login/', permanent=False), name='home'),
    path('login/', LoginPageView.as_view(), name='login-page'),
    path('api-home/', api_home, name='api-home'),

    # Admin
    path('admin/', admin.site.urls),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # App URLs
    path('api/v1/auth/', include('apps.authentication.urls')),
    path('api/auth/', include('apps.authentication.urls')),
    path('api/v1/profile/', include('apps.profile.urls')),
    path('api/profile/', include('apps.profile.urls')),
    path('api/tokens/', include('apps.tokens.urls')),
    path('api/v1/tokens/', include('apps.tokens.urls')),
    path('api/security/', include('apps.security_photos.urls')),
    path('api/v1/photos/', include('apps.security_photos.urls')),
    path('api/v1/face-recognition/', include('apps.facerecognition.urls')),

    # Health check
    path('health/', include('apps.core.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
