"""
URL Configuration for Smart Campus Token Management System
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

from apps.authentication.views import LoginPageView, RegistrationPageView
from apps.core.views import LandingPageView, api_home

urlpatterns = [
    path('', LandingPageView.as_view(), name='home'),
    path('login/', LoginPageView.as_view(), name='login-page'),
    path('register/', RegistrationPageView.as_view(), name='register-page'),
    path('api-home/', api_home, name='api-home'),

    # Admin
    path('admin/', admin.site.urls),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # App URLs
    path('api/v1/auth/', include(('apps.authentication.urls', 'authentication'), namespace='authentication')),
    path('api/auth/', include(('apps.authentication.urls', 'authentication'), namespace='authentication_legacy')),
    path('api/v1/profile/', include(('apps.profile.urls', 'profile'), namespace='profile')),
    path('api/profile/', include(('apps.profile.urls', 'profile'), namespace='profile_legacy')),
    path('api/tokens/', include(('apps.tokens.urls', 'tokens'), namespace='tokens_legacy')),
    path('api/v1/tokens/', include(('apps.tokens.urls', 'tokens'), namespace='tokens')),
    path('api/security/', include(('apps.security_photos.urls', 'security_photos'), namespace='security_photos_legacy')),
    path('api/v1/photos/', include(('apps.security_photos.urls', 'security_photos'), namespace='security_photos')),
    path('api/v1/face-recognition/', include(('apps.facerecognition.urls', 'facerecognition'), namespace='facerecognition')),

    # Health check
    path('health/', include('apps.core.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
