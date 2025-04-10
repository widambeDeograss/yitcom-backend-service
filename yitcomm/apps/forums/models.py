from django.db import models

from yitcomm.apps.accounts.models import TechCategory, User

# Create your models here.

class Forum(models.Model):
    """Discussion forums organized by topic."""
    title = models.CharField(max_length=100)
    description = models.TextField()
    category = models.ForeignKey(TechCategory, on_delete=models.CASCADE, related_name='forums')
    created_at = models.DateTimeField(auto_now_add=True)
    moderators = models.ManyToManyField(User, related_name='moderated_forums', blank=True)
    
    def __str__(self):
        return self.title


class Discussion(models.Model):
    """Discussion threads within forums."""
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='discussions')
    forum = models.ForeignKey(Forum, on_delete=models.CASCADE, related_name='discussions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_pinned = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)
    views = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return self.title