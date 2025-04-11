from rest_framework import serializers

from yitcomm.apps.accounts.serializers import TechCategorySerializer, UserProfileSerializer
from .models import Forum, Discussion, Comment, Reaction

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

class DiscussionSerializer(serializers.ModelSerializer):
    author = UserProfileSerializer(read_only=True)
    forum = serializers.PrimaryKeyRelatedField(read_only=True)
    reactions = ReactionSerializer(many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    user_reaction = serializers.SerializerMethodField()
    
    class Meta:
        model = Discussion
        fields = ('id', 'title', 'content', 'author', 'forum',
                 'created_at', 'updated_at', 'is_pinned', 'is_locked',
                 'views', 'reactions', 'comments', 'user_reaction')
        read_only_fields = ('created_at', 'updated_at', 'views')

    def get_user_reaction(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            reaction = obj.reactions.filter(user=user).first()
            return reaction.reaction if reaction else None
        return None

class ForumSerializer(serializers.ModelSerializer):
    category = TechCategorySerializer(read_only=True)
    discussion_count = serializers.IntegerField(read_only=True)
    latest_discussion = serializers.SerializerMethodField()
    
    class Meta:
        model = Forum
        fields = ('id', 'title', 'description', 'category',
                 'created_by', 'created_at', 'discussion_count',
                 'latest_discussion', 'is_public', 'is_locked', )
        read_only_fields = ('created_at', 'discussion_count')

    def get_latest_discussion(self, obj):
        discussion = obj.discussions.order_by('-created_at').first()
        return DiscussionSerializer(discussion, context=self.context).data if discussion else None

class ForumCreateSerializer(ForumSerializer):
    category = serializers.PrimaryKeyRelatedField(queryset=TechCategory.objects.all())
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)