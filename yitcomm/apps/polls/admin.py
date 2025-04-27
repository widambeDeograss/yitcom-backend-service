from django.contrib import admin

from .models import PollOption, PollVote, TechPoll

# Register your models here.
class PollOptionInline(admin.TabularInline):
    model = PollOption
    extra = 1

@admin.register(TechPoll)
class TechPollAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_by', 'starts_at', 'ends_at', 'published', 'drafted')
    list_filter = ('published', 'drafted')
    search_fields = ('title', 'description')
    inlines = [PollOptionInline]
    date_hierarchy = 'created_at'

@admin.register(PollVote)
class PollVoteAdmin(admin.ModelAdmin):
    list_display = ('user', 'poll', 'option', 'voted_at')
    list_filter = ('voted_at',)
    search_fields = ('user__username', 'poll__title')
    date_hierarchy = 'voted_at'

@admin.register(PollOption)
class PollOptionAdmin(admin.ModelAdmin):
        list_display = ('text', 'poll')
        list_filter = ('poll',)
        search_fields = ('text', 'poll__title')