from django.contrib import admin
from .models import User, Skill, TechCategory, CommunityRole, Notification, Bookmark
from django.contrib.auth.models import Group

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'email', 'first_name', 'last_name', 'is_verified', 'is_deleted', 'created_at')
    search_fields = ('username', 'email')
    list_filter = ('is_verified', 'is_deleted', 'created_at')
    ordering = ('-created_at',)
    readonly_fields = ('date_joined',)

@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')

@admin.register(TechCategory)
class TechCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description', 'parent', 'created_at')
    list_filter = ('parent',)
    search_fields = ('name',)
    ordering = ('-created_at',)

@admin.register(CommunityRole)
class CommunityRoleAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'message', 'created_at', 'is_read')

@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'bookmark_type', 'content_type', 'object_id', 'is_private', 'created_at')
    list_filter = ('bookmark_type', 'is_private', 'content_type', 'created_at')
    search_fields = ('user__username', 'notes', 'folder')
    raw_id_fields = ('user',)
    ordering = ('-created_at',)
        
  