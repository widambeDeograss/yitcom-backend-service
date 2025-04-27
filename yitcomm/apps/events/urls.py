from django.urls import path
from .views import (
    EventListCreateView,
    EventICalView,
    EventRetrieveUpdateDestroyView,
    TechNewsListCreateView,
    NotificationListView,
    EventFeaturedView
)

urlpatterns = [
    path('events/', EventListCreateView.as_view(), name='event-list'),
    path('events/<int:pk>/ical/', EventICalView.as_view(), name='event-ical'),
    path('news/', TechNewsListCreateView.as_view(), name='news-list'),
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('events/<int:pk>/', EventRetrieveUpdateDestroyView.as_view(), name='event-detail'),
    path('featured-events/', EventFeaturedView.as_view(), name='event-FEATURED'),
]