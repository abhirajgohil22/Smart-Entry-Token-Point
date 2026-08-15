"""URL routing for profile management endpoints."""

from django.urls import path

from apps.profile.views import ProfileAPIView, ProfileAvatarUploadAPIView

app_name = 'profile'

urlpatterns = [
    path('', ProfileAPIView.as_view(), name='profile-detail'),
    path('avatar/', ProfileAvatarUploadAPIView.as_view(), name='avatar-upload'),
]
