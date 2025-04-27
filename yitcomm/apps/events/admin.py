from django.contrib import admin
from .models import Event, EventImage, EventRegistration, TechNews

# Register your models here.
@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_time', 'end_time', 'status', 'organizer')
    list_filter = ('status', 'is_online', 'requires_registration')
    search_fields = ('title', 'description', 'location')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'start_time'

@admin.register(EventImage)
class EventImageAdmin(admin.ModelAdmin):
    list_display = ('event', 'caption', 'order')
    list_filter = ('event',)
    search_fields = ('caption', 'event__title')

@admin.register(EventRegistration)
class EventRegistrationAdmin(admin.ModelAdmin):
    list_display = ('event', 'user', 'registered_at', 'attended', 'waitlisted')
    list_filter = ('attended', 'waitlisted')
    search_fields = ('event__title', 'user__email')

@admin.register(TechNews)
class TechNewsAdmin(admin.ModelAdmin):
    list_display = ('title', 'news_type', 'published_at', 'is_featured')
    list_filter = ('news_type', 'is_featured')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'published_at'