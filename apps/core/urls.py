"""
Core app URL configuration
"""

from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('check/', views.health_check, name='health-check'),
]
