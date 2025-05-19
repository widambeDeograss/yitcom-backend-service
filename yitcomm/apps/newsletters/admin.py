from django.contrib import admin

from .models import Newsletter,NewsletterSubscription

# Register your models here.
admin.site.register(Newsletter)
admin.site.register(NewsletterSubscription)