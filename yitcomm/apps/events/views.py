from datetime import timezone
from warnings import filters
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from icalendar import Calendar, Event as ICalEvent
from .models import Event, TechNews
from .serializers import EventSerializer, NotificationSerializer, TechNewsSerializer
from .tasks import send_event_notification, send_news_notification

class EventICalView(APIView):
    def get(self, request, pk):
        event = get_object_or_404(Event, pk=pk)
        cal = Calendar()
        ical_event = ICalEvent()
        ical_event.add('summary', event.title)
        ical_event.add('dtstart', event.start_time)
        ical_event.add('dtend', event.end_time)
        ical_event.add('location', event.location or event.meeting_url)
        ical_event.add('description', event.description)
        cal.add_component(ical_event)

        response = HttpResponse(cal.to_ical(), content_type='text/calendar')
        response['Content-Disposition'] = f'attachment; filename="{event.slug}.ics"'
        return response

class EventListCreateView(generics.ListCreateAPIView):
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['title', 'description']
    filterset_fields = ['categories', 'status', 'is_online']

    def get_queryset(self):
        return Event.objects.prefetch_related('categories', 'registrations')

    def perform_create(self, serializer):
        event = serializer.save(organizer=self.request.user)
        send_event_notification.delay(event.id)

class TechNewsListCreateView(generics.ListCreateAPIView):
    serializer_class = TechNewsSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['title', 'content']
    filterset_fields = ['categories', 'news_type', 'is_featured']

    def get_queryset(self):
        return TechNews.objects.filter(expiry_date__gte=timezone.now())

    def perform_create(self, serializer):
        news = serializer.save(author=self.request.user)
        send_news_notification.delay(news.id)

class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.request.user.notifications.filter(read=False)