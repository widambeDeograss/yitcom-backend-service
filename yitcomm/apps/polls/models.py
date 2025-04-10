from django.db import models
from django.utils import timezone
from yitcomm.apps.accounts.models import User, TechCategory

class TechPoll(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_polls')
    created_at = models.DateTimeField(auto_now_add=True)
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField()
    categories = models.ManyToManyField(TechCategory, related_name='polls')
    featured_image = models.ImageField(upload_to='poll_images/', blank=True, null=True)
    published = models.BooleanField(default=False)
    drafted = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-ends_at', 'published']),
        ]
    
    def __str__(self):
        return self.title
    
    @property
    def is_active(self):
        now = timezone.now()
        return self.published and self.starts_at <= now <= self.ends_at

class PollOption(models.Model):
    poll = models.ForeignKey(TechPoll, on_delete=models.CASCADE, related_name='options')
    text = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return self.text

class PollVote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='poll_votes')
    poll = models.ForeignKey(TechPoll, on_delete=models.CASCADE, related_name='votes')
    option = models.ForeignKey(PollOption, on_delete=models.CASCADE, related_name='votes')
    voted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'poll')
        indexes = [
            models.Index(fields=['-voted_at']),
        ]