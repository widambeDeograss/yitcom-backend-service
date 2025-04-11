from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

class Blog(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique_for_date='published_at')
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blogs')
    categories = models.ManyToManyField(TechCategory, related_name='blogs')
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

class Reaction(models.Model):
    REACTION_TYPES = (
        ('clap', '👏'),
        ('like', '👍'),
        ('dislike', '👎'),
        ('heart', '❤️'),
        ('rocket', '🚀'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
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
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
        ]

    def __str__(self):
        return f"Comment by {self.author} on {self.content_object}"