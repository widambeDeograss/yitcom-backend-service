from asyncio import Event
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from apps.accounts.models import Notification

from .models import EventRegistration
import logging

logger = logging.getLogger(__name__)


# Signal to create notifications when a user registers for an event
# @receiver(post_save, sender=EventRegistration)
def create_registration_notifications(sender, instance, created, **kwargs):
    if created:
        logger.info(f"New registration created for event {instance.event.title} by user {instance.user.username}")
        # Notify the user who registered
        Notification.objects.create(
            user=instance.user,
            notification_type='event_registration',
            title=f"Registration Confirmed: {instance.event.title}",
            message=f"You have successfully registered for {instance.event.title} on {instance.event.start_time.strftime('%B %d, %Y')}.",
            content_type=ContentType.objects.get_for_model(Event),
            object_id=instance.event.id
        )
        
        # Notify the event organizer
        Notification.objects.create(
            user=instance.event.organizer,
            notification_type='new_registration',
            title=f"New Registration: {instance.event.title}",
            message=f"{instance.user.get_full_name()} has registered for your event {instance.event.title}.",
            content_type=ContentType.objects.get_for_model(Event),
            object_id=instance.event.id
        )
        
        # If the event is now full, notify the organizer
        if instance.event.is_full:
            Notification.objects.create(
                user=instance.event.organizer,
                notification_type='event_full',
                title=f"Event Full: {instance.event.title}",
                message=f"Your event {instance.event.title} has reached its maximum capacity of {instance.event.max_participants} participants.",
                content_type=ContentType.objects.get_for_model(Event),
                object_id=instance.event.id
            )