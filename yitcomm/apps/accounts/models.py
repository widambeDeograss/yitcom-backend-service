# core/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

class User(AbstractUser):
    """Extended User model with additional fields for Youth in Tech Tanzania platform."""
    bio = models.TextField(blank=True)
    profile_image = models.ImageField(upload_to='profile_images/', blank=True, null=True)
    github_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    website = models.URLField(blank=True)
    skills = models.ManyToManyField('Skill', blank=True)
    interests = models.ManyToManyField('TechCategory', blank=True, related_name='interested_users')
    is_verified = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    date_of_birth = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_activity = models.DateTimeField(default=timezone.now)
    groups = models.ManyToManyField(
        Group,
        related_name="custom_user_groups",
        blank=True,
        help_text="The groups this user belongs to."
    )

    user_permissions = models.ManyToManyField(
        Permission,
        related_name="custom_user_permissions",
        blank=True,
        help_text="Specific permissions for this user."
    )
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['email']),
            models.Index(fields=['is_verified']),
        ]
        ordering = ['-created_at']

        
    def __str__(self):
        return self.username


class Skill(models.Model):
    """Technical skills that users can add to their profiles."""
    name = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.name


class TechCategory(models.Model):
    """Categories for organizing tech content (blogs, news, projects, etc.)."""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='subcategories')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "Tech Categories"
        indexes = [
            models.Index(fields=['name']),
        ]
        ordering = ['-created_at']
        
    def __str__(self):
        return self.name
    

class Notification(models.Model):
    """User notifications for various activities."""
    NOTIFICATION_TYPES = (
        ('blog', 'New Blog Post'),
        ('comment', 'New Comment'),
        ('event', 'Event Reminder'),
        ('forum', 'Forum Activity'),
        ('project', 'Project Update'),
        ('poll', 'New Poll'),
        ('newsletter', 'Newsletter'),
        ('follow', 'New Follower'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    
    # Generic foreign key to the content that triggered the notification
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "NOtifications"
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['notification_type']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.notification_type} for {self.user.username}: {self.title}"


class UserFollowing(models.Model):
    """Follow relationships between users."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    following_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "User Followings"
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['following_user']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
        unique_together = ('user', 'following_user')
    
    def __str__(self):
        return f"{self.user.username} follows {self.following_user.username}"


# Custom Groups
class CommunityRole(models.Model):
    """Custom roles for the community with extended permissions."""
    name = models.CharField(max_length=100, unique=True)
    group = models.OneToOneField(Group, on_delete=models.CASCADE, related_name='community_role')
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name
    

class Bookmark(models.Model):
    """Generic bookmark system for saving any type of content."""
    BOOKMARK_TYPES = (
        ('blog', 'Blog Post'),
        ('project', 'Project'),
        ('forum', 'Forum'),
        ('discussion', 'Discussion'),
        ('event', 'Event'),
        ('resource', 'Resource'),
        ('user', 'User Profile'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    bookmark_type = models.CharField(max_length=20, choices=BOOKMARK_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Generic foreign key to the bookmarked content
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    
    # Optional fields
    notes = models.TextField(blank=True, null=True)
    is_private = models.BooleanField(default=False)
    folder = models.CharField(max_length=100, blank=True, null=True)
    
    class Meta:
        verbose_name = "Bookmark"
        verbose_name_plural = "Bookmarks"
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['bookmark_type']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']
        unique_together = ('user', 'content_type', 'object_id')  # Prevent duplicate bookmarks
    
    def __str__(self):
        return f"{self.user.username} bookmarked {self.bookmark_type} #{self.object_id}"