from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import RegisterView, SecureTokenObtainPairView, PasswordResetRequestView, PasswordResetConfirmView, MeView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', SecureTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('password-reset/', PasswordResetRequestView.as_view(), name='password_reset'),
    path('password-reset-confirm/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('me/', MeView.as_view(), name='me'),
]