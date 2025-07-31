from rest_framework import serializers
from icalendar import Calendar, Event as ICalEvent
from django.utils import timezone
from django.urls import reverse

from apps.accounts.models import Notification
from apps.accounts.serializers import TechCategorySerializer, UserProfileSerializer
from .models import Event, EventImage, EventRegistration, TechNews, PaymentTransaction, EventTicket


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


class EventImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventImage
        fields = ('id', 'image', 'caption', 'order')


class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = (
            'id', 'order_id', 'amount', 'currency', 'payment_method',
            'payment_reference', 'transaction_id', 'phone_number',
            'status', 'created_at', 'completed_at'
        )
        read_only_fields = ('id', 'created_at', 'completed_at')


class EventTicketSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source='registration.event.title', read_only=True)
    event_date = serializers.DateTimeField(source='registration.event.start_time', read_only=True)
    event_location = serializers.CharField(source='registration.event.location', read_only=True)
    attendee_name = serializers.CharField(source='registration.user.get_full_name', read_only=True)
    qr_code_url = serializers.SerializerMethodField()

    class Meta:
        model = EventTicket
        fields = (
            'id', 'ticket_number', 'qr_code_data', 'qr_code_url',
            'issued_date', 'status', 'used_date', 'event_title',
            'event_date', 'event_location', 'attendee_name', 'is_valid'
        )
        read_only_fields = (
            'id', 'ticket_number', 'qr_code_data', 'issued_date',
            'status', 'used_date', 'is_valid'
        )

    def get_qr_code_url(self, obj):
        if obj.qr_code:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.qr_code.url)
        return None


class EventRegistrationSerializer(serializers.ModelSerializer):
    user = UserProfileSerializer(read_only=True)
    event = serializers.PrimaryKeyRelatedField(read_only=True)
    event_title = serializers.CharField(source='event.title', read_only=True)
    event_price = serializers.DecimalField(source='event.price', max_digits=10, decimal_places=2, read_only=True)
    event_type = serializers.CharField(source='event.event_type', read_only=True)
    ticket = EventTicketSerializer(read_only=True)
    latest_transaction = serializers.SerializerMethodField()
    can_download_ticket = serializers.SerializerMethodField()

    class Meta:
        model = EventRegistration
        fields = (
            'id', 'event', 'event_title', 'event_price', 'event_type',
            'user', 'registration_date', 'status', 'payment_status',
            'payment_order_id', 'payment_reference', 'payment_transaction_id',
            'payment_channel', 'payment_phone', 'amount_paid', 'payment_date',
            'special_requirements', 'attended', 'check_in_time',
            'ticket', 'latest_transaction', 'is_confirmed', 'can_download_ticket'
        )
        read_only_fields = (
            'id', 'registration_date', 'payment_order_id', 'payment_reference',
            'payment_transaction_id', 'payment_channel', 'payment_date',
            'amount_paid', 'attended', 'check_in_time', 'is_confirmed'
        )

    def get_latest_transaction(self, obj):
        transaction = obj.transactions.order_by('-created_at').first()
        if transaction:
            return PaymentTransactionSerializer(transaction, context=self.context).data
        return None

    def get_can_download_ticket(self, obj):
        return obj.is_confirmed and hasattr(obj, 'ticket')


class EventSerializer(serializers.ModelSerializer):
    organizer = UserProfileSerializer(read_only=True)
    categories = TechCategorySerializer(many=True, read_only=True)
    participant_count = serializers.SerializerMethodField()
    confirmed_registrations_count = serializers.IntegerField(read_only=True)
    user_registration = serializers.SerializerMethodField()
    status = serializers.CharField(read_only=True)
    ical_url = serializers.SerializerMethodField()
    images = EventImageSerializer(many=True, read_only=True)
    is_free = serializers.BooleanField(read_only=True)
    available_spots = serializers.IntegerField(read_only=True)
    registration_deadline = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = (
            'id', 'title', 'slug', 'description', 'organizer', 'location',
            'is_online', 'meeting_url', 'start_time', 'end_time', 'timezone',
            'categories', 'featured_image', 'max_participants', 'status',
            'participant_count', 'confirmed_registrations_count', 'user_registration',
            'requires_registration', 'ical_url', 'is_full', 'google_form_url',
            'images', 'event_type', 'price', 'is_free', 'available_spots',
            'registration_deadline'
        )
        read_only_fields = (
            'slug', 'created_at', 'status', 'is_full', 'is_free',
            'available_spots', 'confirmed_registrations_count'
        )

    def get_participant_count(self, obj):
        """Get total registrations (including pending payments)"""
        return obj.registrations.count()

    def get_user_registration(self, obj):
        """Get user's registration details if authenticated"""
        user = self.context['request'].user
        if user.is_authenticated:
            registration = obj.registrations.filter(user=user).first()
            if registration:
                return EventRegistrationSerializer(registration, context=self.context).data
        return None

    def get_ical_url(self, obj):
        request = self.context.get('request')
        if request:
            from django.urls import reverse
            return request.build_absolute_uri(
                reverse('event-ical', kwargs={'pk': obj.pk})
            )
        return None

    def get_registration_deadline(self, obj):
        """Registration deadline (event start time)"""
        return obj.start_time

    def validate(self, data):
        if data.get('start_time') and data.get('end_time'):
            if data['start_time'] >= data['end_time']:
                raise serializers.ValidationError("End time must be after start time")

        # Validate price for paid events
        if data.get('event_type') == 'paid' and data.get('price', 0) <= 0:
            raise serializers.ValidationError("Paid events must have a price greater than 0")

        return data


class PaymentInitiationSerializer(serializers.Serializer):
    """Serializer for payment initiation request"""
    phone_number = serializers.CharField(
        max_length=15,
        help_text="Phone number in format 07XXXXXXXX or +255XXXXXXXXX"
    )

    def validate_phone_number(self, value):
        """Validate Tanzanian phone number format"""
        import re

        # Remove any non-digit characters except +
        clean_phone = re.sub(r'[^\d+]', '', value)

        # Check various formats
        if re.match(r'^(\+255|255)?[67]\d{8}$', clean_phone):
            return clean_phone
        elif re.match(r'^0[67]\d{8}$', clean_phone):
            return clean_phone

        raise serializers.ValidationError(
            "Invalid phone number format. Use format: 07XXXXXXXX or +255XXXXXXXXX"
        )


class PaymentStatusSerializer(serializers.Serializer):
    """Serializer for payment status response"""
    payment_status = serializers.CharField()
    registration_status = serializers.CharField()
    is_confirmed = serializers.BooleanField()
    message = serializers.CharField()
    transaction_details = PaymentTransactionSerializer(required=False)


class TicketVerificationSerializer(serializers.Serializer):
    """Serializer for ticket QR code verification"""
    qr_data = serializers.CharField()

    def validate_qr_data(self, value):
        """Validate QR code data format"""
        parts = value.split(':')
        if len(parts) != 6 or parts[0] != 'event':
            raise serializers.ValidationError("Invalid QR code format")
        return value


class TicketVerificationResponseSerializer(serializers.Serializer):
    """Serializer for ticket verification response"""
    valid = serializers.BooleanField()
    message = serializers.CharField(required=False)
    ticket_number = serializers.CharField(required=False)
    attendee_name = serializers.CharField(required=False)
    event_title = serializers.CharField(required=False)
    status = serializers.CharField(required=False)


class BulkRegistrationSerializer(serializers.Serializer):
    """Serializer for bulk registration (for organizers)"""
    users = serializers.ListField(
        child=serializers.EmailField(),
        help_text="List of user email addresses to register"
    )
    send_notifications = serializers.BooleanField(default=True)


class EventAttendeeSerializer(serializers.ModelSerializer):
    """Serializer for event attendee management"""
    user = UserProfileSerializer(read_only=True)
    ticket = EventTicketSerializer(read_only=True)

    class Meta:
        model = EventRegistration
        fields = (
            'id', 'user', 'registration_date', 'status', 'payment_status',
            'amount_paid', 'payment_date', 'special_requirements',
            'attended', 'check_in_time', 'ticket', 'is_confirmed'
        )
        read_only_fields = (
            'id', 'registration_date', 'amount_paid', 'payment_date'
        )


class NotificationSerializer(serializers.ModelSerializer):
    content_object_url = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = (
            'id', 'notification_type', 'title', 'message', 'content_object',
            'content_object_url', 'read', 'created_at'
        )
        read_only_fields = ('content_object', 'created_at')

    def get_content_object_url(self, obj):
        """Generate URL for the related content object"""
        if obj.content_object:
            request = self.context.get('request')
            if request and isinstance(obj.content_object, Event):
                from django.urls import reverse
                return request.build_absolute_uri(
                    reverse('event-detail', kwargs={'pk': obj.content_object.pk})
                )
        return None


# Custom serializers for specific API responses
class RegistrationResponseSerializer(serializers.Serializer):
    """Response serializer for registration endpoint"""
    success = serializers.BooleanField()
    message = serializers.CharField()
    registration_id = serializers.UUIDField(required=False)
    payment_required = serializers.BooleanField(default=False)
    payment_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    next_step = serializers.CharField(required=False)


class PaymentCallbackSerializer(serializers.Serializer):
    """Serializer for ZenoPay callback data"""
    order_id = serializers.CharField()
    payment_status = serializers.CharField()
    reference = serializers.CharField(required=False)
    transid = serializers.CharField(required=False)
    channel = serializers.CharField(required=False)
    msisdn = serializers.CharField(required=False)
    amount = serializers.CharField(required=False)
    creation_date = serializers.CharField(required=False)