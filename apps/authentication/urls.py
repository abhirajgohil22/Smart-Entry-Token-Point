"""Authentication app URL configuration."""

from django.urls import path

from apps.authentication.views import RegisterAPIView, RegistrationPageView

app_name = 'authentication'

urlpatterns = [
    path('register/', RegisterAPIView.as_view(), name='register'),
    path('register-page/', RegistrationPageView.as_view(), name='register-page'),
]
