from apps.accounts.models import Notification, TechCategory, User
from django.db import models
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MinValueValidator
from decimal import Decimal
import uuid
import qrcode
from io import BytesIO
from django.core.files import File
from apps.accounts.models import Notification, TechCategory, User


class Event(models.Model):
    EVENT_STATUS = (
        ('upcoming', 'Upcoming'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled')
    )

    EVENT_TYPES = (
        ('free', 'Free Event'),
        ('paid', 'Paid Event'),
    )

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique_for_date='start_time')
    description = models.TextField()
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organized_events')
    location = models.CharField(max_length=200, blank=True)
    is_online = models.BooleanField(default=False)
    meeting_url = models.URLField(blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    categories = models.ManyToManyField(TechCategory, related_name='events')
    featured_image = models.ImageField(upload_to='event_images/', blank=True, null=True)
    max_participants = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=EVENT_STATUS, default='upcoming')
    requires_registration = models.BooleanField(default=True)
    timezone = models.CharField(max_length=50, default='UTC')
    featured = models.BooleanField(default=False)

    # Payment related fields
    event_type = models.CharField(max_length=10, choices=EVENT_TYPES, default='free')
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Price in TZS"
    )

    # External registration via Google Form (for free events)
    google_form_url = models.URLField(blank=True, help_text="Optional Google Form URL for external registration")

    # Add generic relation to allow notifications about this event
    notifications = GenericRelation(Notification)

    class Meta:
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['-start_time']),
            models.Index(fields=['status']),
            models.Index(fields=['event_type']),
        ]

    def __str__(self):
        return self.title

    @property
    def is_full(self):
        if self.max_participants:
            return self.confirmed_registrations_count >= self.max_participants
        return False

    @property
    def confirmed_registrations_count(self):
        """Count only confirmed registrations (paid for paid events, confirmed for free events)"""
        if self.event_type == 'free':
            return self.registrations.filter(status='confirmed').count()
        else:
            return self.registrations.filter(payment_status='completed').count()

    @property
    def available_spots(self):
        if self.max_participants:
            return max(0, self.max_participants - self.confirmed_registrations_count)
        return None

    @property
    def duration(self):
        return self.end_time - self.start_time

    @property
    def is_free(self):
        return self.event_type == 'free' or self.price == 0

    def can_register(self, user):
        """Check if a user can register for this event"""
        # Check if event is not full
        if self.is_full:
            return False, "Event is full"

        # Check if user already registered
        if self.registrations.filter(user=user).exists():
            return False, "You are already registered for this event"

        # Check if event is still upcoming
        if self.status != 'upcoming':
            return False, "Registration is not available for this event"

        # Check if registration deadline hasn't passed (assuming registration closes at event start)
        if timezone.now() >= self.start_time:
            return False, "Registration deadline has passed"

        return True, "Can register"


class EventRegistration(models.Model):
    REGISTRATION_STATUS = (
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('canceled', 'Canceled'),
        ('waitlisted', 'Waitlisted'),
    )

    PAYMENT_STATUS = (
        ('pending', 'Pending Payment'),
        ('processing', 'Processing Payment'),
        ('completed', 'Payment Completed'),
        ('failed', 'Payment Failed'),
        ('refunded', 'Refunded'),
        ('not_required', 'Payment Not Required'),
    )

    # id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_registrations')

    # Registration details
    registration_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=REGISTRATION_STATUS, default='pending')

    # Payment details
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='not_required')
    payment_order_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    payment_transaction_id = models.CharField(max_length=100, blank=True, null=True)
    payment_channel = models.CharField(max_length=50, blank=True, null=True)  # e.g., MPESA-TZ
    payment_phone = models.CharField(max_length=15, blank=True, null=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    payment_date = models.DateTimeField(null=True, blank=True)

    # Additional info
    special_requirements = models.TextField(blank=True, help_text="Dietary restrictions, accessibility needs, etc.")
    attended = models.BooleanField(default=False)
    check_in_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['event', 'user']
        ordering = ['-registration_date']
        indexes = [
            models.Index(fields=['payment_status']),
            models.Index(fields=['status']),
            models.Index(fields=['payment_order_id']),
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.event.title}"

    def save(self, *args, **kwargs):
        # Set payment status based on event type
        if self.event.is_free and self.payment_status == 'not_required':
            self.payment_status = 'not_required'
            if self.status == 'pending':
                self.status = 'confirmed'  # Auto-confirm free events

        # Generate unique payment order ID for paid events
        if self.event.event_type == 'paid' and not self.payment_order_id:
            self.payment_order_id = str(uuid.uuid4())
            self.payment_status = 'pending'

        super().save(*args, **kwargs)

        # Generate ticket after successful registration
        if self.status == 'confirmed' or (self.event.event_type == 'paid' and self.payment_status == 'completed'):
            self.generate_ticket()

    def generate_ticket(self):
        """Generate a ticket for confirmed registration"""
        ticket, created = EventTicket.objects.get_or_create(
            registration=self,
            defaults={
                'ticket_number': self.generate_ticket_number(),
                'qr_code_data': f"event:{self.event.id}:registration:{self.id}:user:{self.user.id}"
            }
        )
        if created:
            ticket.generate_qr_code()
        return ticket

    def generate_ticket_number(self):
        """Generate a unique ticket number"""
        from datetime import datetime
        date_str = datetime.now().strftime("%Y%m%d")
        return f"TKT-{self.event.id}-{date_str}-{str(self.id)[:8].upper()}"

    @property
    def is_confirmed(self):
        """Check if registration is confirmed (paid for paid events, confirmed for free events)"""
        if self.event.is_free:
            return self.status == 'confirmed'
        else:
            return self.payment_status == 'completed'

    def initiate_payment(self):
        """Initiate payment process for paid events"""
        if self.event.is_free:
            return {'success': False, 'message': 'This is a free event'}

        if self.payment_status not in ['pending', 'failed']:
            return {'success': False, 'message': 'Payment already processed or in progress'}

        # Here you would integrate with ZenoPay API
        # This is a placeholder for the actual payment initiation
        self.payment_status = 'processing'
        self.save()

        return {
            'success': True,
            'message': 'Payment initiated',
            'order_id': self.payment_order_id
        }


class EventTicket(models.Model):
    TICKET_STATUS = (
        ('active', 'Active'),
        ('used', 'Used'),
        ('canceled', 'Canceled'),
        ('expired', 'Expired'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    registration = models.OneToOneField(EventRegistration, on_delete=models.CASCADE, related_name='ticket')
    ticket_number = models.CharField(max_length=50, unique=True)
    qr_code = models.ImageField(upload_to='tickets/qr_codes/', blank=True, null=True)
    qr_code_data = models.TextField()

    issued_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=TICKET_STATUS, default='active')
    used_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-issued_date']
        indexes = [
            models.Index(fields=['ticket_number']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Ticket {self.ticket_number} - {self.registration.event.title}"

    def generate_qr_code(self):
        """Generate QR code for the ticket"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(self.qr_code_data)
        qr.make(fit=True)

        qr_image = qr.make_image(fill_color="black", back_color="white")

        # Save QR code to model
        buffer = BytesIO()
        qr_image.save(buffer, format='PNG')
        file_name = f'ticket_{self.ticket_number}_qr.png'
        self.qr_code.save(file_name, File(buffer), save=False)
        buffer.close()

        self.save()

    def mark_as_used(self):
        """Mark ticket as used during check-in"""
        if self.status == 'active':
            self.status = 'used'
            self.used_date = timezone.now()
            self.registration.attended = True
            self.registration.check_in_time = timezone.now()
            self.registration.save()
            self.save()
            return True
        return False

    @property
    def is_valid(self):
        """Check if ticket is valid for use"""
        return (
                self.status == 'active' and
                self.registration.is_confirmed and
                self.registration.event.start_time > timezone.now()
        )


class PaymentTransaction(models.Model):
    """Track all payment transactions"""
    TRANSACTION_STATUS = (
        ('initiated', 'Initiated'),
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('canceled', 'Canceled'),
        ('refunded', 'Refunded'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    registration = models.ForeignKey(EventRegistration, on_delete=models.CASCADE, related_name='transactions')

    # ZenoPay specific fields
    order_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='TZS')

    # Payment details
    payment_method = models.CharField(max_length=50, blank=True)  # MPESA-TZ, etc.
    payment_reference = models.CharField(max_length=100, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)

    # Status tracking
    status = models.CharField(max_length=20, choices=TRANSACTION_STATUS, default='initiated')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # API response data
    api_response = models.JSONField(default=dict, blank=True)
    callback_data = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['order_id']),
            models.Index(fields=['status']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Transaction {self.order_id} - {self.amount} {self.currency}"

    def mark_completed(self, callback_data=None):
        """Mark transaction as completed"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        if callback_data:
            self.callback_data = callback_data

        # Update registration
        self.registration.payment_status = 'completed'
        self.registration.payment_date = timezone.now()
        self.registration.amount_paid = self.amount
        self.registration.status = 'confirmed'

        if callback_data:
            self.registration.payment_reference = callback_data.get('reference', '')
            self.registration.payment_transaction_id = callback_data.get('transid', '')
            self.registration.payment_channel = callback_data.get('channel', '')

        self.registration.save()
        self.save()

    def mark_failed(self, reason=''):
        """Mark transaction as failed"""
        self.status = 'failed'
        self.registration.payment_status = 'failed'
        self.api_response['failure_reason'] = reason
        self.registration.save()
        self.save()


class EventImage(models.Model):
    """Model to store multiple images for an event"""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='event_images/')
    caption = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.event.title} - Image {self.order}"


# Signal handlers for automatic processing
from django.db.models.signals import post_save
from django.dispatch import receiver


# @receiver(post_save, sender=EventRegistration)
def handle_registration_confirmation(sender, instance, created, **kwargs):
    """Handle post-registration actions"""
    if created:
        # Send registration confirmation notification
        if instance.event.is_free:
            # For free events, create notification immediately
            Notification.objects.create(
                user=instance.user,
                notification_type="event",
                title=f"Registration Confirmed: {instance.event.title}",
                message=f"You have successfully registered for {instance.event.title}",
                content_type=ContentType.objects.get_for_model(Event),
                object_id=instance.event.id
            )
        else:
            # For paid events, create payment pending notification
            Notification.objects.create(
                 user=instance.user,
                notification_type="event",
                title=f"Registration Confirmed: {instance.event.title}",
                message=f"Please complete payment to confirm your registration for {instance.event.title}",
                content_type=ContentType.objects.get_for_model(Event),
                object_id=instance.event.id
            )


@receiver(post_save, sender=PaymentTransaction)
def handle_payment_completion(sender, instance, **kwargs):
    """Handle payment completion notifications"""
    if instance.status == 'completed':
        # Send payment confirmation notification
        Notification.objects.create(
            user=instance.registration.user,
            notification_type="event",
            title=f"Payment Confirmed: {instance.registration.event.title}",
            message=f"Your payment has been confirmed. Your ticket is ready!",
            content_type=ContentType.objects.get_for_model(Event),
            object_id=instance.registration.event.id
        )

class TechNews(models.Model):
    NEWS_TYPES = (
        ('internal', 'Internal'),
        ('external', 'External'),
        ('announcement', 'Announcement')
    )
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique_for_date='published_at')
    content = models.TextField()
    source_url = models.URLField(blank=True)
    news_type = models.CharField(max_length=20, choices=NEWS_TYPES, default='internal')
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    categories = models.ManyToManyField(TechCategory, related_name='news')
    published_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    featured_image = models.ImageField(upload_to='news_images/', blank=True, null=True)
    is_featured = models.BooleanField(default=False)
    expiry_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Tech News"
        ordering = ['-published_at']
        indexes = [
            models.Index(fields=['-published_at']),
            models.Index(fields=['is_featured']),
        ]

    def __str__(self):
        return self.title


