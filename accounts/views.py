from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView
from .serializers import RegisterSerializer, PasswordResetRequestSerializer, PasswordResetConfirmSerializer

User = get_user_model()

LOGIN_ATTEMPT_LIMIT = 5
LOGIN_LOCKOUT_SECONDS = 300


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class SecureTokenObtainPairView(TokenObtainPairView):
    """
    Wraps the default JWT login view with account-lockout protection.
    Tracks failed attempts per-username in cache; after LOGIN_ATTEMPT_LIMIT
    failures, blocks further attempts for LOGIN_LOCKOUT_SECONDS regardless
    of which IP they come from.
    """
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request, *args, **kwargs):
        username = request.data.get('username', '')
        cache_key = f'login_attempts:{username}'
        attempts = cache.get(cache_key, 0)

        if attempts >= LOGIN_ATTEMPT_LIMIT:
            return Response(
                {'detail': 'Account temporarily locked due to too many failed login attempts. Try again in a few minutes.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        response = super().post(request, *args, **kwargs)

        if response.status_code == 200:
            cache.delete(cache_key)
        else:
            cache.set(cache_key, attempts + 1, LOGIN_LOCKOUT_SECONDS)

        return response


class PasswordResetRequestView(generics.GenericAPIView):
    serializer_class = PasswordResetRequestSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data['email']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Always return the same response whether or not the email exists —
            # prevents attackers from using this endpoint to enumerate valid accounts.
            return Response({'detail': 'If that email exists, a reset link has been sent.'})

        token = PasswordResetTokenGenerator().make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        reset_link = f"http://localhost:8000/api/auth/password-reset-confirm/?uid={uid}&token={token}"

        send_mail(
            subject="Password Reset Request",
            message=f"Use this link to reset your password: {reset_link}",
            from_email="noreply@taskflow.local",
            recipient_list=[email],
        )
        return Response({'detail': 'If that email exists, a reset link has been sent.'})


class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        uid = serializer.validated_data['uid']
        token = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_id)
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            return Response({'detail': 'Invalid reset link.'}, status=status.HTTP_400_BAD_REQUEST)

        if not PasswordResetTokenGenerator().check_token(user, token):
            return Response({'detail': 'Invalid or expired reset link.'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        return Response({'detail': 'Password has been reset successfully.'})