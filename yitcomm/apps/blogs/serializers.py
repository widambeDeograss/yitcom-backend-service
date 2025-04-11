from rest_framework import serializers

from yitcomm.apps.accounts.serializers import UserProfileSerializer
from .models import Blog, Reaction, Comment

class ReactionSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = Reaction
        fields = ('id', 'user', 'reaction_type', 'created_at')
        read_only_fields = ('user', 'created_at')

class CommentSerializer(serializers.ModelSerializer):
    author = UserProfileSerializer(read_only=True)
    reactions = ReactionSerializer(many=True, read_only=True)
    user_reaction = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()
    
    class Meta:
        model = Comment
        fields = ('id', 'content', 'author', 'parent', 'created_at', 
                 'updated_at', 'reactions', 'user_reaction', 'replies')
        read_only_fields = ('created_at', 'updated_at', 'deleted', 'draft')

    def get_replies(self, obj):
        return CommentSerializer(
            obj.replies.all().order_by('created_at')[:5], 
            many=True,
            context=self.context
        ).data

    def get_user_reaction(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            reaction = obj.reactions.filter(user=user).first()
            return reaction.reaction_type if reaction else None
        return None

class BlogSerializer(serializers.ModelSerializer):
    author = UserProfileSerializer(read_only=True)
    categories = TechCategorySerializer(many=True, read_only=True)
    reactions = ReactionSerializer(many=True, read_only=True)
    user_reaction = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
    
    class Meta:
        model = Blog
        fields = ('id', 'title', 'slug', 'content', 'author', 'categories',
                 'published_at', 'is_published', 'featured_image', 'views',
                 'reactions', 'user_reaction', 'comments')
        read_only_fields = ('slug', 'views', 'published_at')

    def get_user_reaction(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            reaction = obj.reactions.filter(user=user).first()
            return reaction.reaction_type if reaction else None
        return None

    def get_comments(self, obj):
        comments = obj.comments.filter(parent__isnull=True).order_by('-created_at')[:10]
        return CommentSerializer(comments, many=True, context=self.context).data