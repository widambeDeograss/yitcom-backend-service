from django.db import models
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from apps.accounts.models import TechCategory, User

class Event(models.Model):
    EVENT_STATUS = (
        ('upcoming', 'Upcoming'),
        ('ongoing', 'Ongoing'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled')
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

    class Meta:
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['-start_time']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return self.title

    @property
    def is_full(self):
        if self.max_participants:
            return self.registrations.count() >= self.max_participants
        return False

    @property
    def duration(self):
        return self.end_time - self.start_time

class EventRegistration(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_registrations')
    registered_at = models.DateTimeField(auto_now_add=True)
    attended = models.BooleanField(default=False)
    waitlisted = models.BooleanField(default=False)

    class Meta:
        unique_together = ('event', 'user')
        ordering = ['registered_at']

    def __str__(self):
        return f"{self.user} - {self.event}"

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

