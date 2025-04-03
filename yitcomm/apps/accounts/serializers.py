from rest_framework import serializers
from django.contrib.auth.models import Group, Permission
from .models import User, Skill, TechCategory, CommunityRole, Notification

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
