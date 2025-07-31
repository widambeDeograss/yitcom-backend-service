from django.urls import path
# api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views as api_views

# Create router for ViewSets (if you have any)
router = DefaultRouter()

app_name = 'api'

urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),

    # Event management
    path('events/', api_views.EventListCreateView.as_view(), name='event-list'),
    path('events/<int:pk>/', api_views.EventRetrieveUpdateDestroyView.as_view(), name='event-detail'),
    path('events/<int:pk>/ical/', api_views.EventICalView.as_view(), name='event-ical'),
    path('events/<int:pk>/register/', api_views.EventRetrieveUpdateDestroyView.as_view(), name='event-register'),
    path('events/<int:pk>/attendees/', api_views.EventRetrieveUpdateDestroyView.as_view(), name='event-attendees'),
    path('events/<int:pk>/bulk-register/', api_views.EventRetrieveUpdateDestroyView.as_view(),
         name='event-bulk-register'),
    path('events/<int:pk>/stats/', api_views.EventStatsView.as_view(), name='event-stats'),
    path('events/featured/', api_views.EventFeaturedView.as_view(), name='event-featured'),

    # Registration management
    path('registrations/<uuid:registration_id>/', api_views.EventRegistrationView.as_view(),
         name='registration-detail'),
    path('registrations/', api_views.UserRegistrationsView.as_view(), name='user-registrations'),

    # Payment endpoints
    path('payments/<uuid:registration_id>/initiate/', api_views.PaymentView.as_view(), name='payment-initiate'),
    path('payments/<uuid:registration_id>/status/', api_views.PaymentView.as_view(), name='payment-status'),
    path('payments/callback/', api_views.zenopay_callback, name='payment-callback'),
    path('payment-methods/', api_views.payment_methods, name='payment-methods'),

    # Ticket management
    path('tickets/', api_views.UserTicketsView.as_view(), name='user-tickets'),
    path('tickets/<uuid:ticket_id>/', api_views.TicketView.as_view(), name='ticket-detail'),
    path('tickets/<uuid:ticket_id>/download/', api_views.TicketView.as_view(), name='ticket-download'),
    path('tickets/<uuid:ticket_id>/checkin/', api_views.checkin_attendee, name='ticket-checkin'),
    path('tickets/verify/', api_views.verify_ticket, name='ticket-verify'),

    # News management
    path('news/', api_views.TechNewsListCreateView.as_view(), name='news-list'),

    # Notifications
    path('notifications/', api_views.NotificationListView.as_view(), name='notification-list'),
    path('notifications/<int:notification_id>/read/', api_views.mark_notification_read, name='notification-read'),
    path('notifications/mark-all-read/', api_views.mark_all_notifications_read, name='notifications-mark-all-read'),

    # User dashboard
    path('dashboard/stats/', api_views.user_dashboard_stats, name='dashboard-stats'),
]