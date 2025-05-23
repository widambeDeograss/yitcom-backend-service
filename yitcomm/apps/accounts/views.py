from rest_framework import viewsets, status, permissions, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from django.contrib.auth.models import Group, Permission
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from social_django.utils import psa
from .models import User, Skill, TechCategory, CommunityRole, Notification
from .models import Bookmark
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from .serializers import BookmarkSerializer, BookmarkCreateSerializer
from .serializers import (
    UserSerializer, 
    UserProfileSerializer, 
    SkillSerializer,
    TechCategorySerializer, 
    CommunityRoleSerializer,
    GroupSerializer,
    PermissionSerializer
)


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Users with full CRUD operations
    """
    queryset = User.objects.filter(is_deleted=False)
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        # Use a simplified serializer for list views
        if self.action == 'list':
            return UserProfileSerializer
        return UserSerializer
    
    def perform_destroy(self, instance):
        # Soft delete
        instance.is_deleted = True
        instance.save()
    
    @action(detail=True, methods=['post'])
    def add_skill(self, request, pk=None):
        user = self.get_object()
        skill_id = request.data.get('skill_id')
        
        try:
            skill = Skill.objects.get(id=skill_id)
            user.skills.add(skill)
            return Response({'status': 'Skill added'}, status=status.HTTP_200_OK)
        except Skill.DoesNotExist:
            return Response({'error': 'Skill not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def remove_skill(self, request, pk=None):
        user = self.get_object()
        skill_id = request.data.get('skill_id')
        
        try:
            skill = Skill.objects.get(id=skill_id)
            user.skills.remove(skill)
            return Response({'status': 'Skill removed'}, status=status.HTTP_200_OK)
        except Skill.DoesNotExist:
            return Response({'error': 'Skill not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def add_interest(self, request, pk=None):
        user = self.get_object()
        category_id = request.data.get('category_id')
        
        try:
            category = TechCategory.objects.get(id=category_id)
            user.interests.add(category)
            return Response({'status': 'Interest added'}, status=status.HTTP_200_OK)
        except TechCategory.DoesNotExist:
            return Response({'error': 'Category not found'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def remove_interest(self, request, pk=None):
        user = self.get_object()
        category_id = request.data.get('category_id')
        
        try:
            category = TechCategory.objects.get(id=category_id)
            user.interests.remove(category)
            return Response({'status': 'Interest removed'}, status=status.HTTP_200_OK)
        except TechCategory.DoesNotExist:
            return Response({'error': 'Category not found'}, status=status.HTTP_404_NOT_FOUND)

class RegisterView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Send welcome email with error handling
            # try:
            #     subject = "Welcome to Youth in Tech Tanzania"
            #     message = (
            #         f"Hello {user.first_name},\n\n"
            #         f"Thank you for registering with Youth in Tech Tanzania. "
            #         f"Your account has been created successfully.\n\n"
            #         f"Best regards,\nYouth in Tech Tanzania Team"
            #     )
            #     send_mail(
            #         subject,
            #         message,
            #         settings.DEFAULT_FROM_EMAIL,
            #         [user.email],
            #         fail_silently=False,
            #     )
            # except Exception as e:
            #     # Log the error but don't fail the registration
            #     print(f"Failed to send welcome email: {e}")
            
            return Response({
                'user': UserSerializer(user).data,
                'message': 'User registered successfully.'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class LoginView(APIView):
    """
    API endpoint for user login with username and password
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')
        
        user = authenticate(username=username, password=password)
        
        if user is None:
            return Response({'error': 'Invalid username or password'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate user is not deleted
        if user.is_deleted:
            return Response({'error': 'User account has been deactivated'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': UserProfileSerializer(user).data
        }, status=status.HTTP_200_OK)


class SocialAuthView(APIView):
    """
    API endpoint for social authentication
    """
    permission_classes = [permissions.AllowAny]
    
    @psa('social:complete')
    def post(self, request, backend, *args, **kwargs):
        """
        Exchange the OAuth token for JWT tokens
        """
        token = request.data.get('access_token')
        if not token:
            return Response({'error': 'No token provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Authenticate via the social backend
        try:
            user = request.backend.do_auth(token)
            if user:
                # Check if user is marked as deleted
                if hasattr(user, 'is_deleted') and user.is_deleted:
                    return Response({'error': 'User account has been deactivated'}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                
                # Generate JWT tokens
                refresh = RefreshToken.for_user(user)
                
                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'user': UserProfileSerializer(user).data
                }, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Authentication failed'}, 
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SkillViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Skills
    """
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class TechCategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Tech Categories
    """
    queryset = TechCategory.objects.all()
    serializer_class = TechCategorySerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    @action(detail=False, methods=['get'])
    def root_categories(self, request):
        """Return only root categories (those without parents)"""
        root_categories = TechCategory.objects.filter(parent__isnull=True)
        serializer = self.get_serializer(root_categories, many=True)
        return Response(serializer.data)


class CommunityRoleViewSet(viewsets.ModelViewSet):
    """
    API endpoint for Community Roles
    """
    queryset = CommunityRole.objects.all()
    serializer_class = CommunityRoleSerializer
    permission_classes = [permissions.IsAuthenticated]


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint for User Groups
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [permissions.IsAdminUser]


class PermissionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing Permissions (read-only)
    """
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializer
    permission_classes = [permissions.IsAdminUser]


class BookmarkListView(generics.ListCreateAPIView):
    serializer_class = BookmarkSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return BookmarkCreateSerializer
        return BookmarkSerializer

    def get_queryset(self):
        return Bookmark.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class BookmarkDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = BookmarkSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Bookmark.objects.filter(user=self.request.user)

class CheckBookmarkView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        content_type = request.query_params.get('content_type')
        object_id = request.query_params.get('object_id')

        if not content_type or not object_id:
            return Response(
                {'error': 'content_type and object_id parameters are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            content_type = ContentType.objects.get(model=content_type)
            is_bookmarked = Bookmark.objects.filter(
                user=request.user,
                content_type=content_type,
                object_id=object_id
            ).exists()
            return Response({'is_bookmarked': is_bookmarked})
        except ContentType.DoesNotExist:
            return Response(
                {'error': 'Invalid content_type'},
                status=status.HTTP_400_BAD_REQUEST
            )


class ToggleBookmarkView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        content_type = request.data.get('content_type')
        object_id = request.data.get('object_id')
        bookmark_type = request.data.get('bookmark_type')

        if not all([content_type, object_id, bookmark_type]):
            return Response(
                {'error': 'content_type, object_id and bookmark_type are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            content_type = ContentType.objects.get(model=content_type)
            bookmark, created = Bookmark.objects.get_or_create(
                user=request.user,
                content_type=content_type,
                object_id=object_id,
                defaults={'bookmark_type': bookmark_type}
            )

            if not created:
                bookmark.delete()
                return Response({'status': 'unbookmarked'})

            return Response({'status': 'bookmarked'}, status=status.HTTP_201_CREATED)
        except ContentType.DoesNotExist:
            return Response(
                {'error': 'Invalid content_type'},
                status=status.HTTP_400_BAD_REQUEST
            )