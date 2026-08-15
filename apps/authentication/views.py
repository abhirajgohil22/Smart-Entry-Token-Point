import os

from django.conf import settings
from django.contrib.auth import authenticate
from django.utils import timezone
from django.views.generic import TemplateView
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.serializers import LoginSerializer, RegistrationSerializer
from apps.authentication.throttles import LoginRateThrottle
from apps.security_photos.models import SecurityPhoto


class RegistrationPageView(TemplateView):
    template_name = 'auth/register.html'


class RegisterAPIView(generics.CreateAPIView):
    serializer_class = RegistrationSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                'message': 'Registration successful. Check your email for the OTP verification code.',
                'user_id': str(user.pk),
                'email': user.email,
                'otp_required': True,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginAPIView(generics.CreateAPIView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [LoginRateThrottle]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        live_photo = serializer.validated_data['live_photo']

        SecurityPhoto.objects.create(
            user=user,
            event_type='LOGIN',
            image=live_photo,
            request_id=f'login-{user.pk}-{os.urandom(4).hex()}',
            nonce=f'login-nonce-{user.pk}-{os.urandom(6).hex()}',
            captured_at=timezone.now(),
            verification_status='PENDING',
            face_recognition_status='NOT_RUN',
            ip_address=getattr(request, 'META', {}).get('REMOTE_ADDR', '127.0.0.1'),
            user_agent=getattr(request, 'META', {}).get('HTTP_USER_AGENT', ''),
        )

        refresh = RefreshToken.for_user(user)
        response_payload = {
            'message': 'Login successful.',
            'email': user.email,
            'user_id': str(user.pk),
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }
        return Response(response_payload, status=status.HTTP_200_OK)


class GoogleOAuthLoginAPIView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        provider = request.data.get('provider', 'google')
        oauth_token = request.data.get('oauth_token')
        if provider.lower() != 'google' or not oauth_token:
            return Response({'error': 'Google OAuth token is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # This is a lightweight integration boundary: allauth can validate the token in
        # production, but the application enforces the same live-photo requirement before
        # issuing JWTs.
        user = authenticate(request, oauth_token=oauth_token)
        if user is None:
            return Response({'error': 'Google authentication failed.'}, status=status.HTTP_400_BAD_REQUEST)

        if not user.is_active:
            return Response({'error': 'This account is inactive.'}, status=status.HTTP_400_BAD_REQUEST)

        live_photo = request.FILES.get('live_photo')
        if not live_photo:
            return Response({'live_photo': ['A live photo is required for Google login.']}, status=status.HTTP_400_BAD_REQUEST)

        validated = LoginSerializer(data={'email': user.email, 'password': 'oauth-login', 'live_photo': live_photo})
        validated.is_valid(raise_exception=True)

        refresh = RefreshToken.for_user(user)
        return Response({
            'message': 'Google login successful.',
            'email': user.email,
            'user_id': str(user.pk),
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_200_OK)


class GoogleOAuthCallbackAPIView(generics.GenericAPIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        return Response({
            'message': 'Google OAuth2 flow started. Complete the live-photo challenge before final JWT issuance.',
            'provider': 'google',
            'requires_live_photo': True,
        }, status=status.HTTP_200_OK)
