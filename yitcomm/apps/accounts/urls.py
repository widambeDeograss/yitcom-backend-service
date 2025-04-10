from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SocialAuthView,
    UserViewSet,
    RegisterView,
    LoginView,
    SkillViewSet,
    TechCategoryViewSet,
    CommunityRoleViewSet,
    GroupViewSet,
    PermissionViewSet,

    
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
]

urlpatterns = [
    path('', include(router.urls)),
    path('auth/', include(auth_urls)),
    path('api/social-auth/<str:backend>/', SocialAuthView.as_view(), name='social_auth'),
]