from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError
from .models import TechPoll, PollOption, PollVote
from apps.accounts.serializers import UserProfileSerializer

class PollOptionSerializer(serializers.ModelSerializer):
    vote_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = PollOption
        fields = ['id', 'text', 'order', 'vote_count']
        read_only_fields = ['id']

class TechPollSerializer(serializers.ModelSerializer):
    created_by = UserProfileSerializer(read_only=True)
    options = PollOptionSerializer(many=True)
    total_votes = serializers.IntegerField(read_only=True)
    user_vote = serializers.SerializerMethodField()
    is_active = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = TechPoll
        fields = [
            'id', 'title', 'description', 'created_by', 'created_at',
            'starts_at', 'ends_at', 'categories', 'featured_image',
            'published', 'drafted', 'options', 'total_votes', 'user_vote', 'is_active'
        ]
        read_only_fields = ['created_at', 'total_votes', 'user_vote', 'is_active']
    
    def get_user_vote(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            vote = obj.votes.filter(user=user).first()
            return vote.option.id if vote else None
        return None
    
    def validate(self, data):
        if self.instance and self.instance.published:
            raise ValidationError("Published polls cannot be modified")
        return data
    
    def create(self, validated_data):
        options_data = validated_data.pop('options')
        poll = TechPoll.objects.create(**validated_data)
        for option_data in options_data:
            PollOption.objects.create(poll=poll, **option_data)
        return poll

class PollVoteSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)
    
    class Meta:
        model = PollVote
        fields = ['id', 'user', 'option', 'voted_at']
        read_only_fields = ['user', 'voted_at']
    
    def validate(self, data):
        poll = data['option'].poll
        user = self.context['request'].user
        
        if not poll.is_active:
            raise ValidationError("This poll is not currently active")
        
        if PollVote.objects.filter(poll=poll, user=user).exists():
            raise ValidationError("You have already voted in this poll")
        
        return data
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        validated_data['poll'] = validated_data['option'].poll
        return super().create(validated_data)