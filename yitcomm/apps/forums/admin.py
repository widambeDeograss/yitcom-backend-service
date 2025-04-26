from django.contrib import admin
from .models import Tag, Forum, Forum_tags, Discussion, Comment, Reaction

# Register your models here.
@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')

@admin.register(Forum)
class ForumAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'category', 'created_by', 'is_public', 'is_active', 'deleted')
    list_filter = ('is_public', 'is_active', 'deleted', 'drafted', 'published', 'locked')
    search_fields = ('title', 'description')

@admin.register(Forum_tags)
class ForumTagsAdmin(admin.ModelAdmin):
    list_display = ('forum', 'tag')

@admin.register(Discussion)
class DiscussionAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'author', 'forum', 'created_at', 'is_pinned', 'is_locked')
    list_filter = ('is_pinned', 'is_locked', 'omitted')
    search_fields = ('title', 'content')

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('id', 'author', 'discussion', 'created_at')
    search_fields = ('content',)

@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'content_type', 'object_id', 'reaction', 'created_at')
    list_filter = ('reaction',)