from rest_framework import viewsets, status, permissions, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate
from django.contrib.auth.models import Group, Permission
from django.shortcuts import get_object_or_404
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework_simplejwt.tokens import RefreshToken
import pyotp
import uuid
from django.core.mail import send_mail
from django.conf import settings
from .models import User, Skill, TechCategory, CommunityRole, Notification
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
    """
    API endpoint for user registration
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate a secret key for the user's TOTP device
            secret_key = pyotp.random_base32()
            
            # Create TOTPDevice for the user
            device = TOTPDevice.objects.create(
                user=user,
                name=f"{user.username}'s device",
                confirmed=True,
                key=secret_key
            )
            
            # Send welcome email with instructions
            subject = "Welcome to Youth in Tech Tanzania"
            message = (
                f"Hello {user.first_name},\n\n"
                f"Thank you for registering with Youth in Tech Tanzania. "
                f"Your account has been created successfully.\n\n"
                f"For security purposes, we use two-factor authentication. "
                f"You will receive a one-time password (OTP) via email when you log in.\n\n"
                f"Best regards,\nYouth in Tech Tanzania Team"
            )
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            
            return Response({
                'user': UserSerializer(user).data,
                'message': 'User registered successfully. You will receive OTPs via email when logging in.'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    """
    API endpoint for user login with email-based two-factor authentication
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')
        
        # First factor: Username and password
        user = authenticate(username=username, password=password)
        
        if user is None:
            return Response({'error': 'Invalid username or password'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate user is not deleted
        if user.is_deleted:
            return Response({'error': 'User account has been deactivated'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if TOTP device exists
        try:
            print(f"Checking TOTP device for user: {user.username}")  # Debugging line
            device = TOTPDevice.objects.get(user=user)
        except TOTPDevice.DoesNotExist:
            # Create a device if it doesn't exist
            secret_key = pyotp.random_base32()
            device = TOTPDevice.objects.create(
                user=user,
                name=f"{user.username}'s device",
                confirmed=True,
                key=secret_key
            )
        
        # Generate OTP
        totp = pyotp.TOTP(device.key)
        otp_code = totp.now()

        print(f"Generated OTP: {otp_code}")  # Debugging line
        
        # Send OTP via email
        subject = "Your Login OTP for Youth in Tech Tanzania"
        message = (
            f"Hello {user.first_name},\n\n"
            f"Your one-time password (OTP) for logging into Youth in Tech Tanzania is: {otp_code}\n\n"
            f"This OTP will expire in 30 seconds. If you did not request this login, "
            f"please contact our support team immediately.\n\n"
            f"Best regards,\nYouth in Tech Tanzania Team"
        )
        # send_mail(
        #     subject,
        #     message,
        #     settings.DEFAULT_FROM_EMAIL,
        #     [user.email],
        #     fail_silently=False,
        # )
        
        # Generate a temporary token for the OTP verification step
        temp_token = str(uuid.uuid4())
        
        # Save the temporary token in the session
        request.session['temp_token'] = temp_token
        request.session['user_id'] = user.id
        
        return Response({
            'message': 'First factor authentication successful. Please check your email for OTP.',
            'temp_token': temp_token
        }, status=status.HTTP_200_OK)


# {
#         "password": "123456",
#         "username": "Esmeralda85"
# }

class VerifyOTPView(APIView):
    """
    API endpoint for OTP verification (second factor)
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        otp = request.data.get('otp')
        temp_token = request.data.get('temp_token')
        
        # Validate temporary token
        if not temp_token or temp_token != request.session.get('temp_token'):
            return Response({'error': 'Invalid or expired session'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user_id from session
        user_id = request.session.get('user_id')
        if not user_id:
            return Response({'error': 'Invalid session'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Validate OTP
        try:
            device = TOTPDevice.objects.get(user=user)
            totp = pyotp.TOTP(device.key)
            
            if totp.verify(otp):
                # OTP is valid, generate access token
                refresh = RefreshToken.for_user(user)
                
                # Clean up session
                if 'temp_token' in request.session:
                    del request.session['temp_token']
                if 'user_id' in request.session:
                    del request.session['user_id']
                
                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'user': UserProfileSerializer(user).data
                }, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)
                
        except TOTPDevice.DoesNotExist:
            return Response({'error': 'OTP device not configured'}, status=status.HTTP_400_BAD_REQUEST)


class ResendOTPView(APIView):
    """
    API endpoint for resending OTP
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        temp_token = request.data.get('temp_token')
        
        # Validate temporary token
        if not temp_token or temp_token != request.session.get('temp_token'):
            return Response({'error': 'Invalid or expired session'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get user_id from session
        user_id = request.session.get('user_id')
        if not user_id:
            return Response({'error': 'Invalid session'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({'error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
        
        # Generate new OTP
        try:
            device = TOTPDevice.objects.get(user=user)
            totp = pyotp.TOTP(device.key)
            otp_code = totp.now()
            
            # Send OTP via email
            subject = "Your Login OTP for Youth in Tech Tanzania"
            message = (
                f"Hello {user.first_name},\n\n"
                f"Your new one-time password (OTP) for logging into Youth in Tech Tanzania is: {otp_code}\n\n"
                f"This OTP will expire in 30 seconds. If you did not request this login, "
                f"please contact our support team immediately.\n\n"
                f"Best regards,\nYouth in Tech Tanzania Team"
            )
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            
            return Response({
                'message': 'A new OTP has been sent to your email address.'
            }, status=status.HTTP_200_OK)
                
        except TOTPDevice.DoesNotExist:
            # Create a device if it doesn't exist
            secret_key = pyotp.random_base32()
            device = TOTPDevice.objects.create(
                user=user,
                name=f"{user.username}'s device",
                confirmed=True,
                key=secret_key
            )
            
            # Generate OTP with the new device
            totp = pyotp.TOTP(device.key)
            otp_code = totp.now()
            
            # Send OTP via email
            subject = "Your Login OTP for Youth in Tech Tanzania"
            message = (
                f"Hello {user.first_name},\n\n"
                f"Your one-time password (OTP) for logging into Youth in Tech Tanzania is: {otp_code}\n\n"
                f"This OTP will expire in 30 seconds. If you did not request this login, "
                f"please contact our support team immediately.\n\n"
                f"Best regards,\nYouth in Tech Tanzania Team"
            )
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
            
            return Response({
                'message': 'A new OTP has been sent to your email address.'
            }, status=status.HTTP_200_OK)


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