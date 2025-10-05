from rest_framework import serializers
from django.contrib.auth.models import Group, Permission
from .models import User, Skill, TechCategory, CommunityRole, Notification, Bookmark
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from ..newsletters.signals import send_email_via_smtp


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ('id', 'name', 'codename')

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model =  Notification
        fields = "__all__"


class GroupSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Group
        fields = ('id', 'name', 'permissions')


class CommunityRoleSerializer(serializers.ModelSerializer):
    group = GroupSerializer(read_only=True)
    
    class Meta:
        model = CommunityRole
        fields = ('id', 'name', 'description', 'group')
        

class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ('id', 'name')


class TechCategorySerializer(serializers.ModelSerializer):
    parent_name = serializers.StringRelatedField(source='parent', read_only=True)
    
    class Meta:
        model = TechCategory
        fields = ('id', 'name', 'description', 'parent', 'parent_name')


class UserSerializer(serializers.ModelSerializer):
    skills = SkillSerializer(many=True, read_only=True)
    interests = TechCategorySerializer(many=True, read_only=True)
    groups = serializers.SlugRelatedField(many=True, slug_field='name', queryset=Group.objects.all())
    
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'bio', 
                'profile_image', 'github_url', 'linkedin_url', 'twitter_url', 
                'website', 'skills', 'interests', 'is_verified', 
                'date_of_birth', 'location', 'groups', 'date_joined', 'is_deleted','created_at', 'updated_at', 'password')
        read_only_fields = ('is_verified', 'date_joined', 'created_at', 'updated_at')
        extra_kwargs = {
            'password': {'write_only': True}
        }
    
    def create(self, validated_data):
        groups_data = validated_data.pop('groups', [])
        skills_data = validated_data.pop('skills', [])
        interests_data = validated_data.pop('interests', [])
        
        user = User.objects.create_user(**validated_data)
        
        for group in groups_data:
            user.groups.add(group)
        
        for skill_id in skills_data:
            try:
                skill = Skill.objects.get(id=skill_id)
                user.skills.add(skill)
            except Skill.DoesNotExist:
                pass
        
        for interest_id in interests_data:
            try:
                category = TechCategory.objects.get(id=interest_id)
                user.interests.add(category)
            except TechCategory.DoesNotExist:
                pass
        
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    groups = GroupSerializer(many=True, read_only=True)
    """Simplified user serializer for profile information."""
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'profile_image', "groups", "email", "phone_number", "is_active")



class BookmarkSerializer(serializers.ModelSerializer):
    content_type = serializers.SlugRelatedField(
        queryset=ContentType.objects.all(),
        slug_field='model'
    )
    content_object = serializers.SerializerMethodField()
    is_bookmarked = serializers.SerializerMethodField()

    class Meta:
        model = Bookmark
        fields = [
            'id', 'user', 'bookmark_type', 'content_type', 
            'object_id', 'content_object', 'notes',
            'is_private', 'folder', 'created_at', 'is_bookmarked'
        ]
        read_only_fields = ['user', 'created_at', 'content_object', 'is_bookmarked']

    def get_content_object(self, obj):
        # Serialize the bookmarked object based on its type
        from apps.blogs.serializers import BlogSerializer
        from apps.forums.serializers import ForumSerializer
        
        model = obj.content_type.model
        if model == 'blog':
            return BlogSerializer(obj.content_object).data
        elif model == 'forum':
            return ForumSerializer(obj.content_object).data
        # Add other model serializers as needed
        return None

    def get_is_bookmarked(self, obj):
        # Useful when checking if an item is bookmarked
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Bookmark.objects.filter(
                user=request.user,
                content_type=obj.content_type,
                object_id=obj.object_id
            ).exists()
        return False

    def create(self, validated_data):
        # Automatically set the user to the current user
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class BookmarkCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bookmark
        fields = ['bookmark_type', 'content_type', 'object_id', 'notes', 'folder']


# serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

User = get_user_model()


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile information"""
    date_of_birth = serializers.DateField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            'username', 'email', 'first_name', 'last_name', 'bio',
            'profile_image', 'github_url', 'linkedin_url', 'twitter_url',
            'website', 'phone_number', 'date_of_birth', 'location',
            'skills', 'interests'
        ]
        extra_kwargs = {
            'username': {'required': False},
            'email': {'required': False},
        }

    def validate_username(self, value):
        # Check if username is already taken by another user
        if User.objects.filter(username=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("Username is already taken.")
        return value

    def validate_email(self, value):
        # Check if email is already taken by another user
        if User.objects.filter(email=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("Email is already taken.")
        return value


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change operation"""
    current_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True)
    confirm_password = serializers.CharField(required=True, write_only=True)

    def validate(self, data):
        # Check if new passwords match
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})

        # Validate password strength
        try:
            validate_password(data['new_password'])
        except DjangoValidationError as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})

        return data


class SocialLinksSerializer(serializers.ModelSerializer):
    """Serializer for updating social links only"""

    class Meta:
        model = User
        fields = ['github_url', 'linkedin_url', 'twitter_url', 'website']


# serializers.py
from rest_framework import serializers
from .models import ContactUs


class ContactUsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactUs
        fields = ['id', 'name', 'email', 'subject', 'message', 'submitted_at', 'is_resolved']
        read_only_fields = ['id', 'submitted_at', 'is_resolved']

    def create(self, validated_data):
        # Create the contact us entry
        contact = ContactUs.objects.create(**validated_data)

        # Send confirmation email
        self.send_confirmation_email(contact)

        return contact

    def send_confirmation_email(self, contact):
        """
        Send confirmation email to the person who submitted the contact form
        """
        subject = f"Thank you for contacting us: {contact.subject}"

        html_content = f"""
        <html>
          <head></head>
          <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
              <h2 style="color: #4a6baf;">Thank You for Contacting Us!</h2>
              <p>Dear {contact.name},</p>
              <p>We have received your message and will get back to you as soon as possible.</p>

              <div style="background: #f9f9f9; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>Your Message Details:</strong></p>
                <p><strong>Subject:</strong> {contact.subject}</p>
                <p><strong>Message:</strong> {contact.message}</p>
              </div>

              <p>We typically respond within 24-48 hours.</p>

              <p style="margin-top: 30px; font-size: 0.9em; color: #666;">
                This is an automated response. Please do not reply to this email.
              </p>
            </div>
          </body>
        </html>
        """

        text_content = f"""
        Thank You for Contacting Us!

        Dear {contact.name},

        We have received your message and will get back to you as soon as possible.

        Your Message Details:
        Subject: {contact.subject}
        Message: {contact.message}

        We typically respond within 24-48 hours.

        This is an automated response. Please do not reply to this email.
        """



        print(f"====================SENDING CONTACT US CONFIRMATION TO: {contact.email}")
        send_email_via_smtp(
            recipient=contact.email,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )