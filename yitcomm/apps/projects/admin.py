from django.contrib import admin

from .models import Project

# Register your models here.
@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'created_at', 'published', 'drafted', 'deleted')
    search_fields = ('title', 'description', 'author__username')
    list_filter = ('published', 'drafted', 'deleted', 'categories')
    filter_horizontal = ('contributors', 'categories', 'technologies_used')
    readonly_fields = ('created_at', 'updated_at')