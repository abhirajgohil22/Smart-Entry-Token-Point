"""Authentication app URL configuration."""

from django.urls import path

from apps.authentication.views import (
    LoginAPIView,
    LoginPageView,
    RegisterAPIView,
    RegistrationPageView,
    verify_email,
)

app_name = 'authentication'

urlpatterns = [
    path('register/', RegisterAPIView.as_view(), name='register'),
    path('verify-email/', verify_email, name='verify-email'),
    path('register-page/', RegistrationPageView.as_view(), name='register-page'),
    path('login-page/', LoginPageView.as_view(), name='login-page'),
    path('login/', LoginAPIView.as_view(), name='login'),
]
