from django.utils import timezone
from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

from apps.accounts.models import TechCategory, User
from django.utils.text import slugify


class Blog(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique_for_date='published_at')
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_author')
    categories = models.ManyToManyField(TechCategory, related_name='blog_categories')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(default=False)
    featured_image = models.ImageField(upload_to='blog_images/', blank=True, null=True)
    views = models.PositiveIntegerField(default=0)
    deleted = models.BooleanField(default=False)
    draft = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-published_at']
        indexes = [
            models.Index(fields=['-published_at']),
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        return self.title

    def publish(self):
        self.is_published = True
        self.published_at = timezone.now()
        self.save()

    def save(self, *args, **kwargs):
        # Always generate slug from title
        if not self.slug:
            self.slug = slugify(self.title)

        # Make slug unique by appending counter if needed
        original_slug = self.slug
        counter = 1
        while Blog.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
            self.slug = f"{original_slug}-{counter}"
            counter += 1

        # Set published_at when publishing for the first time
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()

        super().save(*args, **kwargs)

class Reaction(models.Model):
    REACTION_TYPES = (
        ('clap', '👏'),
        ('like', '👍'),
        ('dislike', '👎'),
        ('heart', '❤️'),
        ('rocket', '🚀'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_reactions')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    reaction_type = models.CharField(max_length=10, choices=REACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'content_type', 'object_id')
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]

class Comment(models.Model):
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_comments')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='blog_reactions')
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return f"Comment by {self.author} on {self.content_object}"