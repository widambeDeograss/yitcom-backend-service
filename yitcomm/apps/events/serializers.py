from rest_framework import serializers
from icalendar import Calendar, Event as ICalEvent
from django.utils import timezone
from django.urls import reverse

from apps.accounts.models import Notification
from apps.accounts.serializers import TechCategorySerializer, UserProfileSerializer
from .models import Event, EventRegistration, TechNews

class TechNewsSerializer(serializers.ModelSerializer):
    author = UserProfileSerializer(read_only=True)
    categories = TechCategorySerializer(many=True, read_only=True)
    status = serializers.SerializerMethodField()
    
    class Meta:
        model = TechNews
        fields = ('id', 'title', 'slug', 'content', 'source_url', 'news_type',
                 'author', 'categories', 'published_at', 'is_featured',
                 'featured_image', 'expiry_date', 'status')
        read_only_fields = ('slug', 'created_at', 'updated_at', 'status')

    def get_status(self, obj):
        now = timezone.now()
        if obj.expiry_date and obj.expiry_date < now:
            return 'expired'
        return 'active'

class EventSerializer(serializers.ModelSerializer):
    organizer = UserProfileSerializer(read_only=True)
    categories = TechCategorySerializer(many=True, read_only=True)
    participant_count = serializers.IntegerField(read_only=True)
    user_registered = serializers.SerializerMethodField()
    status = serializers.CharField(read_only=True)
    ical_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = ('id', 'title', 'slug', 'description', 'organizer', 'location',
                 'is_online', 'meeting_url', 'start_time', 'end_time', 'timezone',
                 'categories', 'featured_image', 'max_participants', 'status',
                 'participant_count', 'user_registered', 'requires_registration',
                 'ical_url', 'is_full')
        read_only_fields = ('slug', 'created_at', 'status', 'is_full')

    def get_user_registered(self, obj):
        user = self.context['request'].user
        return obj.registrations.filter(user=user).exists() if user.is_authenticated else False

    def get_ical_url(self, obj):
        return self.context['request'].build_absolute_uri(
            reverse('event-ical', kwargs={'pk': obj.pk})
        )

    def validate(self, data):
        if data['start_time'] >= data['end_time']:
            raise serializers.ValidationError("End time must be after start time")
        return data

class EventRegistrationSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)
    event = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = EventRegistration
        fields = ('id', 'event', 'user', 'registered_at', 'attended', 'waitlisted')
        read_only_fields = ('registered_at', 'attended', 'waitlisted')

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ('id', 'notification_type', 'title', 'message', 'content_object',
                 'read', 'created_at')
        read_only_fields = ('content_object', 'created_at')