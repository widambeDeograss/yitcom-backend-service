from rest_framework import serializers
from apps.accounts.models import Skill, TechCategory, User
from apps.accounts.serializers import SkillSerializer, TechCategorySerializer, UserProfileSerializer
from apps.projects.models import Project

class ProjectSerializer(serializers.ModelSerializer):
    author = UserProfileSerializer(read_only=True)
    author_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='author', write_only=True
    )
    contributors = UserProfileSerializer(many=True, read_only=True)
    contributor_ids = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='contributors', many=True, write_only=True, required=False
    )
    categories = TechCategorySerializer(many=True, read_only=True)
    category_ids = serializers.PrimaryKeyRelatedField(
        queryset=TechCategory.objects.all(), source='categories', many=True, write_only=True
    )
    technologies_used = SkillSerializer(many=True, read_only=True)
    technology_ids = serializers.PrimaryKeyRelatedField(
        queryset=Skill.objects.all(), source='technologies_used', many=True, write_only=True
    )
    
    class Meta:
        model = Project
        fields = ('id', 'title', 'description', 'author', 'author_id', 
                 'contributors', 'contributor_ids', 'github_url', 'project_url',
                 'categories', 'category_ids', 'created_at', 'updated_at',
                 'featured_image', 'technologies_used', 'technology_ids', 'published', 'drafted', 'deleted')
        read_only_fields = ('created_at', 'updated_at')

        def validate(self, data):
            """Ensure published projects can't be drafts"""
            if data.get('published', False) and data.get('drafted', False):
                raise serializers.ValidationError(
                    "A project cannot be both published and drafted."
                )
            return data

        def create(self, validated_data):
            """Set author and default state for new projects"""
            validated_data['author'] = self.context['request'].user
            
            # Default new projects to drafted unless specified otherwise
            if 'drafted' not in validated_data:
                validated_data['drafted'] = True
            if 'published' not in validated_data:
                validated_data['published'] = False
                
            return super().create(validated_data)