from django.urls import path
from .views import (
    NewsletterSubscriptionView,
    SubscriptionPreferencesView,
    NewsletterListView,
    NewsletterManagementView,
    NewsletterSendView
)

urlpatterns = [
    # Subscription endpoints
    path('subscriptions/', NewsletterSubscriptionView.as_view(), 
         name='subscription-list'),
    path('subscriptions/<str:email>/', SubscriptionPreferencesView.as_view(), 
         name='subscription-detail'),
    
    # Newsletter endpoints
    path('', NewsletterListView.as_view(), name='newsletter-list'),
    path('manage/<int:pk>/', NewsletterManagementView.as_view(), 
         name='newsletter-management'),
    path('manage/<int:pk>/send/', NewsletterSendView.as_view(), 
         name='send-newsletter'),
]