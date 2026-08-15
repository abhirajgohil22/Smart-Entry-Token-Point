from django.conf import settings
from django.views.generic import TemplateView
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from apps.authentication.serializers import RegistrationSerializer


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
