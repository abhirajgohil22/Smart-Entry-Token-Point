"""Profile management views with strict security isolation."""

from django.contrib.auth import get_user_model
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from apps.profile.serializers import ProfilePhotoUploadSerializer, ProfileSerializer
from apps.security_photos.models import ProfilePhoto

User = get_user_model()


class ProfileAPIView(generics.RetrieveAPIView):
    """Fetch user profile details, email verification status, and display photo (avatar).
    
    SECURITY: Returns ONLY ProfilePhoto (display picture) and user metadata.
    NEVER returns or exposes SecurityPhoto records.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProfileSerializer

    def get_object(self):
        """Return the ProfilePhoto for the requesting user, or create a wrapper."""
        user = self.request.user
        try:
            profile_photo = user.profile_photo
            return profile_photo
        except ProfilePhoto.DoesNotExist:
            profile_photo = None

        if profile_photo is None:
            profile_photo = type('ProfileWrapper', (object,), {
                'user': user,
                'profile_photo': None,
            })()

        return profile_photo

    def retrieve(self, request, *args, **kwargs):
        """Override to return profile data directly."""
        obj = self.get_object()
        serializer = self.get_serializer(obj)
        return Response(serializer.data)


class ProfileAvatarUploadAPIView(generics.CreateAPIView):
    """Upload or update a user's display picture (avatar).
    
    SECURITY: Stores to ProfilePhoto ONLY, completely isolated from SecurityPhoto.
    Avatar images are for display only and cannot be used for authentication.
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProfilePhotoUploadSerializer

    def create(self, request, *args, **kwargs):
        """Handle avatar upload and store in ProfilePhoto."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.save()

        profile_photo = data['profile_photo']
        response_serializer = ProfilePhotoUploadSerializer(data={'avatar': profile_photo.image})

        return Response(
            {
                'message': 'Avatar uploaded successfully.',
                'avatar_url': request.build_absolute_uri(profile_photo.image.url) if profile_photo.image else None,
                'updated_at': profile_photo.updated_at,
            },
            status=status.HTTP_201_CREATED,
        )
