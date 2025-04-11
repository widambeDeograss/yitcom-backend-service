from django.urls import path
from .views import (
    EventListCreateView,
    EventICalView,
    TechNewsListCreateView,
    NotificationListView
)

urlpatterns = [
    path('events/', EventListCreateView.as_view(), name='event-list'),
    path('events/<int:pk>/ical/', EventICalView.as_view(), name='event-ical'),
    path('news/', TechNewsListCreateView.as_view(), name='news-list'),
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
]