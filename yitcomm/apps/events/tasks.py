# from celery import shared_task
from django.contrib.auth import get_user_model

from apps.accounts.models import Notification
from .models import Event, TechNews


# @shared_task
def send_event_notification(event_id):
    event = Event.objects.get(id=event_id)
    users = get_user_model().objects.all()
    
    for user in users:
        Notification.objects.create(
            user=user,
            notification_type='event',
            title=f"New Event: {event.title}",
            message=event.description[:200],
            content_object=event
        )

# @shared_task
def send_news_notification(news_id):
    news = TechNews.objects.get(id=news_id)
    users = get_user_model().objects.all()
    
    for user in users:
        Notification.objects.create(
            user=user,
            notification_type='news',
            title=f"Tech News: {news.title}",
            message=news.content[:200],
            content_object=news
        )