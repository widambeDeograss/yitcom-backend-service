from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet,
    RegisterView,
    LoginView,
    VerifyOTPView,
    SkillViewSet,
    TechCategoryViewSet,
    CommunityRoleViewSet,
    GroupViewSet,
    PermissionViewSet,
    ResendOTPView,
    
)

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'skills', SkillViewSet)
router.register(r'tech-categories', TechCategoryViewSet)
router.register(r'community-roles', CommunityRoleViewSet)
router.register(r'groups', GroupViewSet)
router.register(r'permissions', PermissionViewSet)

# URLs that don't fit the router pattern
auth_urls = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('resend-otp/', ResendOTPView.as_view(), name='setup-otp'),
]

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include(auth_urls)),
]