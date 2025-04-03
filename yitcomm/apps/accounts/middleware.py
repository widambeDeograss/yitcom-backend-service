from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import UntypedToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.authentication import JWTAuthentication

from django.conf import settings
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class UpdateLastActivityMiddleware:
    """
    Middleware to update user's last activity timestamp
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Update last activity for authenticated users
        if request.user.is_authenticated:
            pass
            User.objects.filter(pk=request.user.pk).update(last_activity=timezone.now())
            
        return response


class CheckUserStatusMiddleware:
    """
    Middleware to check if user is active or deleted
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/api/v1/data') and request.user.is_authenticated:
            # Check if user is deleted
            if request.user.is_deleted:
                raise AuthenticationFailed('User account has been deactivated.')
                
        return self.get_response(request)


class CustomJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication to add additional user checks
    """
    def get_user(self, validated_token):
        try:
            user_id = validated_token['user_id']
            
            try:
                user = User.objects.get(id=user_id)
                
                # Check if user is deleted
                if user.is_deleted:
                    raise AuthenticationFailed('User account has been deactivated.')
                    
                return user
            except User.DoesNotExist:
                raise AuthenticationFailed('User not found.')
                
        except KeyError:
            raise AuthenticationFailed('Invalid token.')


def get_client_ip(request):
    """
    Get client IP address from request
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip