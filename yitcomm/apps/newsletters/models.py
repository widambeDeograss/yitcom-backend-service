from django.db import models

from yitcomm.apps.accounts.models import TechCategory, User

class NewsletterSubscription(models.Model):
    """Newsletter subscription management."""
    email = models.EmailField(unique=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='newsletter_subscriptions')
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    categories = models.ManyToManyField(TechCategory, blank=True, related_name='subscribers')
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return self.email


class Newsletter(models.Model):
    """Newsletters sent to subscribers."""
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_newsletters')
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    categories = models.ManyToManyField(TechCategory, related_name='newsletters')
    
    def __str__(self):
        return self.title
