"""Token generation API views."""

from django.contrib.auth import get_user_model
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tokens.services import TokenGenerationService

User = get_user_model()


class GenerateTokenAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        user_id = request.data.get('user_id') or request.query_params.get('user_id')
        live_photo = request.FILES.get('live_photo')

        if not user_id:
            return Response({'error': 'A user_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if not live_photo:
            return Response(
                {
                    'live_photo': ['A fresh live photo is required to generate a token.'],
                    'error': 'A fresh live photo is required to generate a token.',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(pk=user_id).first()
        if user is None:
            return Response({'error': 'Student not found.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = TokenGenerationService.generate_token(user, live_photo)
        except (ValueError, serializers.ValidationError) as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({'error': f'Token generation failed: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(result, status=status.HTTP_200_OK)


class RegenerateTokenAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        token_id = request.data.get('token_id') or request.query_params.get('token_id')
        user_id = request.data.get('user_id') or request.query_params.get('user_id')
        live_photo = request.FILES.get('live_photo')
        previous_security_photo_id = request.data.get('previous_security_photo_id')

        if not token_id:
            return Response({'error': 'A token_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

        if not live_photo:
            return Response(
                {
                    'live_photo': ['A fresh live photo is required to regenerate a token.'],
                    'error': 'A fresh live photo is required to regenerate a token.',
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        token = None
        if user_id:
            user = User.objects.filter(pk=user_id).first()
            if user is None:
                return Response({'error': 'Student not found.'}, status=status.HTTP_400_BAD_REQUEST)
            token = user.campus_tokens.filter(pk=token_id).first()
        else:
            from apps.tokens.models import CampusToken
            token = CampusToken.objects.filter(pk=token_id).first()

        if token is None:
            return Response({'error': 'Token not found.'}, status=status.HTTP_400_BAD_REQUEST)

        if user_id and str(token.user_id) != str(user_id):
            return Response({'error': 'Token does not belong to this user.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result = TokenGenerationService.regenerate_token(
                token.user,
                token.pk,
                live_photo,
                previous_security_photo_id=previous_security_photo_id,
            )
        except (ValueError, serializers.ValidationError) as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            return Response({'error': f'Token regeneration failed: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(result, status=status.HTTP_200_OK)
