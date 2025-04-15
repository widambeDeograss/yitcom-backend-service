from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from apps.accounts.models import TechCategory, User

class Tag(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class Forum(models.Model):
    """Discussion forums with enhanced moderation"""
    title = models.CharField(max_length=100)
    description = models.TextField()
    category = models.ForeignKey(TechCategory, on_delete=models.CASCADE, related_name='forums')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_forums')
    created_at = models.DateTimeField(auto_now_add=True)
    moderators = models.ManyToManyField(User, related_name='moderated_forums', blank=True)
    is_public = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    featured_image = models.ImageField(upload_to='forum_images/', blank=True, null=True)
    tags = models.ManyToManyField(Tag, blank=True,  through='Forum_tags', related_name='forums_tagged')
    followers = models.ManyToManyField(User, related_name='followed_forums', blank=True)
    followers_count = models.PositiveIntegerField(default=0)
    views = models.PositiveIntegerField(default=0)
    pinned_discussions = models.ManyToManyField('Discussion', blank=True, related_name='pinned_forums')
    deleted = models.BooleanField(default=False)
    drafted = models.BooleanField(default=False)
    published = models.BooleanField(default=False)
    locked = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
      

    def __str__(self):
        return self.title


class Forum_tags(models.Model):
    forum = models.ForeignKey(Forum, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE) 


class Discussion(models.Model):
    """Discussion threads with engagement tracking"""
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='discussions')
    forum = models.ForeignKey(Forum, on_delete=models.CASCADE, related_name='discussions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_pinned = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)
    omitted = models.BooleanField(default=False)
    views = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-is_pinned', '-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return self.title

class Comment(models.Model):
    """Nested comments for discussions"""
    discussion = models.ForeignKey(Discussion, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE)

    class Meta:
        ordering = ['created_at']

class Reaction(models.Model):
    """User reactions to discussions/comments"""
    REACTION_CHOICES = [
        ('👍', 'Thumbs Up'),
        ('❤️', 'Heart'),
        ('🚀', 'Rocket'),
        ('👀', 'Eyes'),
        ('🔥', 'Fire'),
        ('💔', 'Broken Heart'),
        ('🎉', 'Party Popper'),
        ('🤔', 'Thinking Face'),
        ('👎', 'Thumbs Down'),
        ('👏', 'Clapping Hands'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='forum_reactions')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='forum_reactions')
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    reaction = models.CharField(max_length=2, choices=REACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'content_type', 'object_id')



        


