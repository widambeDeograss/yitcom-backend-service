from rest_framework import serializers

from apps.accounts.serializers import TechCategorySerializer, UserProfileSerializer
from apps.accounts.models import TechCategory
from apps.accounts.bookmark_util import get_bookmark_status
from .models import Forum, Discussion, Comment, Reaction
from django.contrib.contenttypes.models import ContentType

class ReactionSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = Reaction
        fields = ('user', 'reaction', 'created_at')
        read_only_fields = ('user', 'created_at')

class CommentSerializer(serializers.ModelSerializer):
    author = UserProfileSerializer(read_only=True)
    reactions = ReactionSerializer(many=True, read_only=True)
    reply_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = ('id', 'author', 'content', 'created_at', 
                 'updated_at', 'parent', 'reactions', 'reply_count')
        read_only_fields = ('created_at', 'updated_at')

    def get_reply_count(self, obj):
        return obj.comment_set.count()


class DiscussionCreateSerializer(serializers.ModelSerializer):
    forum = serializers.PrimaryKeyRelatedField(queryset=Forum.objects.all())
    
    class Meta:
        model = Discussion
        fields = ('title', 'content', 'forum', 'author')
    
    def create(self, validated_data):
        discussion = Discussion.objects.create(**validated_data)
        return discussion
    

class DiscussionSerializer(serializers.ModelSerializer):
    author = UserProfileSerializer(read_only=True)
    forum = serializers.PrimaryKeyRelatedField(read_only=True)
    reactions = serializers.SerializerMethodField()
    comments = CommentSerializer(many=True, read_only=True)
    reactions_count = serializers.SerializerMethodField()
    user_reaction = serializers.SerializerMethodField()
    
    class Meta:
        model = Discussion
        fields = ('id', 'title', 'content', 'author', 'forum',
                 'created_at', 'updated_at', 'is_pinned', 'is_locked',
                 'views', 'reactions', 'comments', 'user_reaction', 'reactions_count')
        read_only_fields = ('created_at', 'updated_at', 'views')
    
    def get_user_reaction(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            reaction = obj.reactions.filter(user=user).first()
            return reaction.reaction if reaction else None
        return None
    
    def get_reactions(self, obj):
        if hasattr(obj, 'prefetched_reactions'):
            return ReactionSerializer(obj.prefetched_reactions, many=True).data
        return ReactionSerializer(obj.reactions.all(), many=True).data
    
    def get_reactions_count(self, obj):
        if hasattr(obj, 'prefetched_reactions'):
            return len(obj.prefetched_reactions)
        return obj.reactions.count()
    

class ForumSerializer(serializers.ModelSerializer):
    category = TechCategorySerializer(read_only=True)
    discussion_count = serializers.IntegerField(read_only=True)
    latest_discussion = serializers.SerializerMethodField()
    created_by = UserProfileSerializer(read_only=True)
    views = serializers.IntegerField(read_only=True)
    bookmark_status = serializers.SerializerMethodField()

    
    class Meta:
        model = Forum
        fields = ('id', 'title', 'description', 'category',
                 'created_by', 'created_at', 'discussion_count',
                 'latest_discussion', 'is_public', 'locked', 'views', 'followers_count')
        read_only_fields = ('created_at', 'discussion_count', 'bookmark_status')
    
    def get_bookmark_status(self, obj):
        request = self.context.get('request')
        return get_bookmark_status(request.user if request else None, obj)

    def get_latest_discussion(self, obj):
        discussion = obj.discussions.order_by('-created_at').first()
        return DiscussionSerializer(discussion, context=self.context).data if discussion else None

class ForumCreateSerializer(ForumSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=TechCategory.objects.all())
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)

class CategoryWithForumStatsSerializer(serializers.ModelSerializer):
    forum_count = serializers.IntegerField(read_only=True)
    active_forum_count = serializers.IntegerField(read_only=True)
    public_forum_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = TechCategory
        fields = ['id', 'name', 'forum_count', 'active_forum_count', 'public_forum_count']