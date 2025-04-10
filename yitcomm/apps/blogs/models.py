from datetime import timezone
from django.db import models

from yitcomm.apps.accounts.models import TechCategory, User

# Create your models here.
class Blog(models.Model):
    """User-created tech blog posts."""
    title = models.CharField(max_length=200)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blogs')
    categories = models.ManyToManyField(TechCategory, related_name='blogs')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    is_published = models.BooleanField(default=False)
    featured_image = models.ImageField(upload_to='blog_images/', blank=True, null=True)
    claps = models.ManyToManyField(User, through='BlogClap', related_name='clapped_blogs')
    views = models.PositiveIntegerField(default=0)
    
    def publish(self):
        self.is_published = True
        self.published_at = timezone.now()
        self.save()
    
    def __str__(self):
        return self.title


class BlogClap(models.Model):
    """Many-to-many relationship for users clapping on blogs."""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'blog')


class Comment(models.Model):
    """Comments on blogs, projects, or forum discussions."""
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Generic foreign key to support comments on different content types
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    
    def __str__(self):
        return f'Comment by {self.author.username} on {self.content_type}'

