"""Serializers for profile management and avatar uploads."""

import os

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.security_photos.models import ProfilePhoto

User = get_user_model()


class ProfilePhotoUploadSerializer(serializers.Serializer):
    """Validate and upload a user profile display picture (avatar)."""

    avatar = serializers.ImageField(required=True, write_only=True, max_length=None)

    def validate_avatar(self, value):
        """Enforce file size and format constraints on display pictures."""
        if value is None:
            raise serializers.ValidationError('Avatar image is required.')

        if not hasattr(value, 'read'):
            raise serializers.ValidationError('Avatar is invalid.')

        value.seek(0, os.SEEK_END)
        size = value.tell()
        value.seek(0)

        if size == 0 or size > 5 * 1024 * 1024:
            raise serializers.ValidationError('Avatar must be between 1 byte and 5 MB.')

        content_type = getattr(value, 'content_type', '') or ''
        allowed_mimes = {'image/jpeg', 'image/png'}
        if content_type and content_type not in allowed_mimes:
            raise serializers.ValidationError('Only PNG and JPEG images are allowed.')

        import imghdr

        if hasattr(value, 'read'):
            chunk = value.read(2048)
            value.seek(0)
            detected = imghdr.what(None, h=chunk)
            if detected not in {'jpeg', 'png'}:
                raise serializers.ValidationError('Avatar is not a valid image.')

        return value

    def create(self, validated_data):
        """Store the avatar in ProfilePhoto and return the user."""
        user = self.context['request'].user
        avatar = validated_data['avatar']

        profile_photo, _ = ProfilePhoto.objects.update_or_create(
            user=user,
            defaults={'image': avatar},
        )

        return {'user': user, 'profile_photo': profile_photo}


class ProfilePhotoSerializer(serializers.ModelSerializer):
    """Serialize a user's display picture (avatar)."""

    url = serializers.SerializerMethodField()

    class Meta:
        model = ProfilePhoto
        fields = ['url', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

    def get_url(self, obj):
        """Return the full avatar URL or None if not set."""
        if obj.image:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None


class ProfileSerializer(serializers.Serializer):
    """Serialize user profile details without exposing security photos."""

    user_id = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    last_name = serializers.SerializerMethodField()
    email_verified = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    def get_user_id(self, obj):
        user = obj.user if hasattr(obj, 'user') else obj
        return str(user.pk)

    def get_email(self, obj):
        user = obj.user if hasattr(obj, 'user') else obj
        return user.email

    def get_first_name(self, obj):
        user = obj.user if hasattr(obj, 'user') else obj
        return user.first_name

    def get_last_name(self, obj):
        user = obj.user if hasattr(obj, 'user') else obj
        return user.last_name

    def get_email_verified(self, obj):
        """Check if user's latest OTP is verified."""
        from apps.authentication.models import EmailOTP

        user = obj.user if hasattr(obj, 'user') else obj
        latest_otp = EmailOTP.objects.filter(user=user).order_by('-created_at').first()
        return latest_otp is not None and latest_otp.is_verified

    def get_avatar(self, obj):
        """Return avatar data if it exists, None otherwise."""
        if isinstance(obj, ProfilePhoto):
            serializer = ProfilePhotoSerializer(obj, context=self.context)
            return serializer.data
        elif hasattr(obj, 'profile_photo'):
            if obj.profile_photo:
                serializer = ProfilePhotoSerializer(obj.profile_photo, context=self.context)
                return serializer.data
        return None


class MinimalProfileSerializer(serializers.Serializer):
    """Minimal profile info for public or list endpoints (no security photo references)."""

    user_id = serializers.CharField()
    email = serializers.CharField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    avatar_url = serializers.CharField(allow_null=True)
