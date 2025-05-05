from rest_framework import serializers
from django.contrib.auth.models import Group, Permission
from .models import User, Skill, TechCategory, CommunityRole, Notification, Bookmark
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ('id', 'name', 'codename')


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
    """Simplified user serializer for profile information."""
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'profile_image')



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
            'object_id', 'content_object', 'notes', 'tags',
            'is_private', 'folder', 'created_at', 'is_bookmarked'
        ]
        read_only_fields = ['user', 'created_at', 'content_object', 'is_bookmarked']

    def get_content_object(self, obj):
        # Serialize the bookmarked object based on its type
        from blogs.serializers import BlogSerializer  # Example import
        from forums.serializers import ForumSerializer  # Example import
        
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