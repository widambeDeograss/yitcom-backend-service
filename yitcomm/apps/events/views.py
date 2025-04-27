from django.urls import reverse
from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from icalendar import Calendar, Event as ICalEvent
from .permissions import IsOrganizerOrAdmin
from .models import Event, EventImage, EventRegistration, TechNews
from .serializers import EventImageSerializer, EventSerializer, NotificationSerializer, TechNewsSerializer
from .tasks import send_event_notification, send_news_notification
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.decorators import action
from django.utils import timezone

class EventICalView(APIView):
    def get(self, request, pk):
        event = get_object_or_404(Event.objects.prefetch_related('images'), pk=pk)
        
        cal = Calendar()
        cal.add('prodid', '-//TechEvents Calendar//mxm.dk//')
        cal.add('version', '2.0')
        
        ical_event = ICalEvent()
        ical_event.add('uid', f'event-{event.pk}@yit-agency.com')
        ical_event.add('summary', event.title)
        ical_event.add('dtstart', event.start_time)
        ical_event.add('dtend', event.end_time)
        ical_event.add('description', event.description)
        
        if event.location:
            ical_event.add('location', event.location)
        elif event.is_online and event.meeting_url:
            ical_event.add('location', event.meeting_url)
        
        # Add URL to the event
        if request:
            event_url = request.build_absolute_uri(f'/api/v1/events/events/{event.pk}/')
            ical_event.add('url', event_url)
        
        # Add organizer info
        ical_event.add('organizer', f"MAILTO:{event.organizer.email}")
        
        cal.add_component(ical_event)

        response = HttpResponse(cal.to_ical(), content_type='text/calendar')
        response['Content-Disposition'] = f'attachment; filename="{event.slug}.ics"'
        return response
     
    @action(detail=True, methods=['POST'], permission_classes=[permissions.IsAuthenticated])
    def upload_images(self, request, pk=None):
        event = self.get_object()
        
        # Check if user is organizer or staff
        if request.user != event.organizer and not request.user.is_staff:
            return Response({"detail": "You don't have permission to upload images to this event."},
                           status=status.HTTP_403_FORBIDDEN)
        
        # Handle multiple image uploads
        images = request.FILES.getlist('images')
        if not images:
            return Response({"detail": "No images provided"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get the next order number
        next_order = EventImage.objects.filter(event=event).count()
        
        # Create event images
        event_images = []
        for img in images:
            event_image = EventImage.objects.create(
                event=event,
                image=img,
                caption=request.data.get('caption', ''),
                order=next_order
            )
            event_images.append(event_image)
            next_order += 1
        
        serializer = EventImageSerializer(event_images, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['POST'], permission_classes=[permissions.IsAuthenticated])
    def register(self, request, pk=None):
        event = self.get_object()
        user = request.user
        
        # Check if registration is required
        if not event.requires_registration:
            if event.google_form_url:
                return Response({
                    "detail": "This event uses external registration. Please use the Google Form.",
                    "google_form_url": event.google_form_url
                }, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({
                    "detail": "This event doesn't require registration."
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if already registered
        if EventRegistration.objects.filter(event=event, user=user).exists():
            return Response({"detail": "You are already registered for this event."}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Check if event is full
        if event.is_full:
            # Add to waitlist
            registration = EventRegistration.objects.create(
                event=event,
                user=user,
                waitlisted=True
            )
            return Response({
                "detail": "Event is full. You have been added to the waitlist.",
                "waitlisted": True
            }, status=status.HTTP_201_CREATED)
        else:
            # Register normally
            registration = EventRegistration.objects.create(
                event=event,
                user=user
            )
            return Response({
                "detail": "Successfully registered for the event.",
                "registration_id": registration.id
            }, status=status.HTTP_201_CREATED)


class EventListCreateView(generics.ListCreateAPIView):
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    filterset_fields = ['categories', 'status', 'is_online']

    def get_queryset(self):
        return Event.objects.prefetch_related(
            'categories', 
            'registrations',
            'images'  # Prefetch related images
        ).order_by('-start_time')

    def perform_create(self, serializer):
        event = serializer.save(organizer=self.request.user)
        send_event_notification.delay(event.id)


class TechNewsListCreateView(generics.ListCreateAPIView):
    serializer_class = TechNewsSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [ DjangoFilterBackend]
    search_fields = ['title', 'content']
    filterset_fields = ['categories', 'news_type', 'is_featured']

    def get_queryset(self):
        return TechNews.objects.filter(expiry_date__gte=timezone.now()).order_by('-published_at')

    def perform_create(self, serializer):
        news = serializer.save(author=self.request.user)
        send_news_notification.delay(news.id)

class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return self.request.user.notifications.filter(read=False)
    

class EventRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """
    View for retrieving, updating and deleting individual events.
    Includes proper handling of featured_image and related images.
    """
    queryset = Event.objects.prefetch_related(
        'images',
        'categories',
        'registrations',
        'organizer'
    )
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = 'pk'

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [permissions.IsAuthenticated(), IsOrganizerOrAdmin()]
        return super().get_permissions()

    def get_serializer_context(self):
        """Add request context to serializer for proper image URL generation"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def update(self, request, *args, **kwargs):
        """Handle partial updates (PATCH) and full updates (PUT)"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Only allow organizer or admin to update
        if not (request.user == instance.organizer or request.user.is_staff):
            return Response(
                {"detail": "You do not have permission to perform this action."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=partial
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        """Handle event deletion with proper permissions"""
        instance = self.get_object()
        
        # Only allow organizer or admin to delete
        if not (request.user == instance.organizer or request.user.is_staff):
            return Response(
                {"detail": "You do not have permission to perform this action."},
                status=status.HTTP_403_FORBIDDEN
            )

        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)
    

class EventFeaturedView(generics.ListAPIView):
    """
    View for listing featured events.
    """
    serializer_class = EventSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return Event.objects.filter(featured=True).order_by('-start_time')