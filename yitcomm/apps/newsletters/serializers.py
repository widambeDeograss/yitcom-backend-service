from rest_framework import serializers
from yitcomm.apps.accounts.models import Skill, TechCategory, User
from yitcomm.apps.accounts.serializers import TechCategorySerializer, UserProfileSerializer
from yitcomm.apps.newsletters.models import Newsletter, NewsletterSubscription

class NewsletterSubscriptionSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)
    categories = TechCategorySerializer(many=True, read_only=True)
    category_ids = serializers.PrimaryKeyRelatedField(
        queryset=TechCategory.objects.all(), source='categories', many=True, write_only=True, required=False
    )
    
    class Meta:
        model = NewsletterSubscription
        fields = ('id', 'email', 'user', 'is_active', 'subscribed_at', 'categories', 'category_ids', 'unsubscribed_at')
        read_only_fields = ('subscribed_at',)


class NewsletterSerializer(serializers.ModelSerializer):
    created_by = UserProfileSerializer(read_only=True)
    created_by_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), source='created_by', write_only=True
    )
    categories = TechCategorySerializer(many=True, read_only=True)
    category_ids = serializers.PrimaryKeyRelatedField(
        queryset=TechCategory.objects.all(), source='categories', many=True, write_only=True
    )
    
    class Meta:
        model = Newsletter
        fields = ('id', 'title', 'content', 'created_by', 'created_by_id',
                 'created_at', 'sent_at', 'categories', 'category_ids')
        read_only_fields = ('created_at', 'sent_at')