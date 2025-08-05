# api_views.py
from django.forms import models
from django.urls import reverse
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.db import transaction
from django.contrib.auth import get_user_model

from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend

from icalendar import Calendar, Event as ICalEvent
import logging
import json

from .permissions import IsOrganizerOrAdmin
from .models import (
    Event, EventImage, EventRegistration, EventTicket,
    PaymentTransaction, TechNews, Notification
)
from .serializers import (
    EventImageSerializer, EventSerializer, EventRegistrationSerializer,
    EventTicketSerializer, PaymentTransactionSerializer, NotificationSerializer,
    TechNewsSerializer, PaymentInitiationSerializer, PaymentStatusSerializer,
    TicketVerificationSerializer, TicketVerificationResponseSerializer,
    BulkRegistrationSerializer, EventAttendeeSerializer, RegistrationResponseSerializer,
    PaymentCallbackSerializer
)
from .zeno_service import ZenoPayService, create_payment_for_registration, check_and_update_payment_status
from .tasks import send_event_notification, send_news_notification

User = get_user_model()
logger = logging.getLogger(__name__)


class EventICalView(APIView):
    """Generate iCal file for events"""

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

        if request:
            event_url = request.build_absolute_uri(f'/api/v1/events/events/{event.pk}/')
            ical_event.add('url', event_url)

        ical_event.add('organizer', f"MAILTO:{event.organizer.email}")
        cal.add_component(ical_event)

        response = HttpResponse(cal.to_ical(), content_type='text/calendar')
        response['Content-Disposition'] = f'attachment; filename="{event.slug}.ics"'
        return response


class EventListCreateView(generics.ListCreateAPIView):
    """List and create events with payment support"""

    serializer_class = EventSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    filterset_fields = ['categories', 'status', 'is_online', 'event_type', 'featured']
    ordering_fields = ['start_time', 'created_at', 'price']
    ordering = ['-start_time']

    def get_queryset(self):
        return Event.objects.prefetch_related(
            'categories',
            'registrations',
            'images'
        ).select_related('organizer')

    def perform_create(self, serializer):
        event = serializer.save(organizer=self.request.user)
        send_event_notification(event.id)


class EventRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update and delete events with enhanced payment features"""

    queryset = Event.objects.prefetch_related(
        'images', 'categories', 'registrations', 'organizer'
    )
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    lookup_field = 'pk'

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsOrganizerOrAdmin()]
        return super().get_permissions()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    @action(detail=True, methods=['POST'], permission_classes=[IsAuthenticated])
    def register(self, request, pk=None):
        """Register for an event with payment support"""
        event = self.get_object()
        user = request.user

        # Validate registration eligibility
        can_register, message = event.can_register(user)
        if not can_register:
            return Response({
                "success": False,
                "message": message
            }, status=status.HTTP_400_BAD_REQUEST)

        # Check if registration is required
        if not event.requires_registration:
            if event.google_form_url:
                return Response({
                    "success": False,
                    "message": "This event uses external registration. Please use the Google Form.",
                    "google_form_url": event.google_form_url
                }, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({
                    "success": False,
                    "message": "This event doesn't require registration."
                }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # Get special requirements from request
                special_requirements = request.data.get('special_requirements', '')

                if event.is_full:
                    # Add to waitlist
                    registration = EventRegistration.objects.create(
                        event=event,
                        user=user,
                        special_requirements=special_requirements,
                        status='waitlisted'
                    )

                    return Response({
                        "success": True,
                        "message": "Event is full. You have been added to the waitlist.",
                        "registration_id": registration.id,
                        "waitlisted": True
                    }, status=status.HTTP_201_CREATED)

                else:
                    # Create registration
                    registration = EventRegistration.objects.create(
                        event=event,
                        user=user,
                        special_requirements=special_requirements
                    )

                    if event.is_free:
                        # Free event - confirm immediately
                        return Response({
                            "success": True,
                            "message": "Successfully registered for the event.",
                            "registration_id": registration.id,
                            "payment_required": False,
                            "next_step": "confirmed"
                        }, status=status.HTTP_201_CREATED)
                    else:
                        # Paid event - payment required
                        return Response({
                            "success": True,
                            "message": "Registration created. Payment required to confirm.",
                            "registration_id": registration.id,
                            "payment_required": True,
                            "payment_amount": event.price,
                            "next_step": "payment"
                        }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Registration error for event {event.id}: {str(e)}")
            return Response({
                "success": False,
                "message": "An error occurred during registration. Please try again."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['POST'], permission_classes=[IsAuthenticated])
    def upload_images(self, request, pk=None):
        """Upload multiple images to an event"""
        event = self.get_object()

        if request.user != event.organizer and not request.user.is_staff:
            return Response({
                "detail": "You don't have permission to upload images to this event."
            }, status=status.HTTP_403_FORBIDDEN)

        images = request.FILES.getlist('images')
        if not images:
            return Response({
                "detail": "No images provided"
            }, status=status.HTTP_400_BAD_REQUEST)

        next_order = EventImage.objects.filter(event=event).count()

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

    @action(detail=True, methods=['GET'], permission_classes=[IsAuthenticated])
    def attendees(self, request, pk=None):
        """Get event attendees (for organizers)"""
        event = self.get_object()

        if request.user != event.organizer and not request.user.is_staff:
            return Response({
                "detail": "You don't have permission to view attendees."
            }, status=status.HTTP_403_FORBIDDEN)

        registrations = event.registrations.select_related('user').prefetch_related('ticket')

        # Filter by status
        status_filter = request.query_params.get('status')
        if status_filter == 'confirmed':
            registrations = registrations.filter(
                models.Q(status='confirmed') |
                models.Q(payment_status='completed')
            )
        elif status_filter:
            registrations = registrations.filter(status=status_filter)

        serializer = EventAttendeeSerializer(registrations, many=True, context={'request': request})

        return Response({
            'attendees': serializer.data,
            'total_registrations': event.registrations.count(),
            'confirmed_registrations': event.confirmed_registrations_count,
            'available_spots': event.available_spots
        })

    @action(detail=True, methods=['POST'], permission_classes=[IsAuthenticated])
    def bulk_register(self, request, pk=None):
        """Bulk register users (for organizers)"""
        event = self.get_object()

        if request.user != event.organizer and not request.user.is_staff:
            return Response({
                "detail": "You don't have permission to bulk register users."
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = BulkRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_emails = serializer.validated_data['users']
        send_notifications = serializer.validated_data['send_notifications']

        registered_users = []
        failed_registrations = []

        for email in user_emails:
            try:
                user = User.objects.get(email=email)
                can_register, message = event.can_register(user)

                if can_register:
                    registration = EventRegistration.objects.create(
                        event=event,
                        user=user
                    )
                    registered_users.append({
                        'email': email,
                        'name': user.get_full_name(),
                        'registration_id': registration.id
                    })
                else:
                    failed_registrations.append({
                        'email': email,
                        'reason': message
                    })

            except User.DoesNotExist:
                failed_registrations.append({
                    'email': email,
                    'reason': 'User not found'
                })

        return Response({
            'registered_users': registered_users,
            'failed_registrations': failed_registrations,
            'total_registered': len(registered_users),
            'total_failed': len(failed_registrations)
        })


class EventRegistrationView(APIView):
    """Handle event registration payments"""
    permission_classes = [IsAuthenticated]

    def get(self, request, registration_id):
        """Get registration details"""
        registration = get_object_or_404(
            EventRegistration.objects.select_related('event', 'user').prefetch_related('ticket'),
            id=registration_id,
            user=request.user
        )

        serializer = EventRegistrationSerializer(registration, context={'request': request})
        return Response(serializer.data)

    def patch(self, request, registration_id):
        """Update registration (cancel, update requirements)"""
        registration = get_object_or_404(
            EventRegistration,
            id=registration_id,
            user=request.user
        )

        # Handle cancellation
        if request.data.get('action') == 'cancel':
            if registration.event.start_time <= timezone.now():
                return Response({
                    "success": False,
                    "message": "Cannot cancel registration - event has already started"
                }, status=status.HTTP_400_BAD_REQUEST)

            registration.status = 'canceled'
            registration.save()

            if hasattr(registration, 'ticket'):
                registration.ticket.status = 'canceled'
                registration.ticket.save()

            return Response({
                "success": True,
                "message": "Registration canceled successfully"
            })

        # Handle other updates
        serializer = EventRegistrationSerializer(
            registration,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)


class PaymentView(APIView):
    """Handle payment operations"""
    permission_classes = [IsAuthenticated]

    def post(self, request, registration_id):
        """Initiate payment for a registration"""
        registration = get_object_or_404(
            EventRegistration,
            id=registration_id,
            user=request.user
        )

        if registration.event.is_free:
            return Response({
                "success": False,
                "message": "This is a free event, no payment required"
            }, status=status.HTTP_400_BAD_REQUEST)

        if registration.payment_status in ['completed', 'processing']:
            return Response({
                "success": False,
                "message": "Payment already processed or in progress"
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = PaymentInitiationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone_number = serializer.validated_data['phone_number']

        # Update user phone if different
        if phone_number != request.user.phone:
            request.user.phone = phone_number
            request.user.save()

        # Initiate payment
        result = create_payment_for_registration(registration)

        if result.get('success'):
            return Response({
                "success": True,
                "message": "Payment initiated successfully. Please complete the payment on your phone.",
                "order_id": result.get('order_id'),
                "transaction_id": result.get('transaction_id')
            })
        else:
            return Response({
                "success": False,
                "message": result.get('error', 'Payment initiation failed')
            }, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, registration_id):
        """Check payment status"""
        registration = get_object_or_404(
            EventRegistration,
            id=registration_id,
            user=request.user
        )

        if registration.payment_order_id:
            result = check_and_update_payment_status(registration)
            registration.refresh_from_db()

            transaction_data = None
            latest_transaction = registration.transactions.order_by('-created_at').first()
            if latest_transaction:
                transaction_data = PaymentTransactionSerializer(latest_transaction).data

            serializer = PaymentStatusSerializer(data={
                'payment_status': registration.payment_status,
                'registration_status': registration.status,
                'is_confirmed': registration.is_confirmed,
                'message': 'Status updated',
                'transaction_details': transaction_data
            })
            serializer.is_valid()

            return Response(serializer.data)
        else:
            return Response({
                "success": False,
                "message": "No payment order found"
            }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([])  # No authentication required for callback
def zenopay_callback(request):
    """Handle payment callback from ZenoPay"""
    try:
        serializer = PaymentCallbackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        callback_data = serializer.validated_data
        logger.info(f"Received ZenoPay callback: {callback_data}")

        zenopay = ZenoPayService()
        success, message = zenopay.process_callback(callback_data)

        if success:
            return Response({'status': 'success', 'message': message})
        else:
            return Response({'status': 'error', 'message': message})

    except Exception as e:
        logger.error(f"Callback processing error: {str(e)}")
        return Response({'status': 'error', 'message': 'Processing error'})


class TicketView(APIView):
    """Handle ticket operations"""
    permission_classes = [IsAuthenticated]

    def get(self, request, ticket_id):
        """Get ticket details"""
        ticket = get_object_or_404(
            EventTicket.objects.select_related('registration__event', 'registration__user'),
            id=ticket_id,
            registration__user=request.user
        )

        if not ticket.registration.is_confirmed:
            return Response({
                "success": False,
                "message": "Cannot access ticket - registration not confirmed"
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = EventTicketSerializer(ticket, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['GET'])
    def download(self, request, ticket_id):
        """Download ticket as PDF"""
        ticket = get_object_or_404(
            EventTicket.objects.select_related('registration__event', 'registration__user'),
            id=ticket_id,
            registration__user=request.user
        )

        if not ticket.registration.is_confirmed:
            return Response({
                "success": False,
                "message": "Cannot download ticket - registration not confirmed"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Generate PDF ticket (you can implement this using reportlab)
        from .utils import generate_ticket_pdf

        pdf_buffer = generate_ticket_pdf(ticket)

        response = HttpResponse(
            pdf_buffer.getvalue(),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'attachment; filename="ticket_{ticket.ticket_number}.pdf"'

        return response


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_ticket(request):
    """Verify ticket QR code (for event organizers/staff)"""
    serializer = TicketVerificationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    qr_data = serializer.validated_data['qr_data']

    try:
        # Parse QR data: "event:ID:registration:ID:user:ID"
        parts = qr_data.split(':')
        event_id = parts[1]
        registration_id = parts[3]
        user_id = parts[5]

        # Find the ticket
        ticket = EventTicket.objects.select_related(
            'registration__event', 'registration__user'
        ).get(
            registration__event_id=event_id,
            registration_id=registration_id,
            registration__user_id=user_id
        )

        # Check if user has permission to verify this ticket
        if (request.user != ticket.registration.event.organizer and
                not request.user.is_staff):
            return Response({
                "valid": False,
                "message": "Permission denied"
            }, status=status.HTTP_403_FORBIDDEN)

        response_serializer = TicketVerificationResponseSerializer(data={
            'valid': ticket.is_valid,
            'ticket_number': ticket.ticket_number,
            'attendee_name': ticket.registration.user.get_full_name(),
            'event_title': ticket.registration.event.title,
            'status': ticket.status,
            'message': 'Ticket verified successfully' if ticket.is_valid else 'Ticket is not valid'
        })
        response_serializer.is_valid()

        return Response(response_serializer.data)

    except (IndexError, ValueError):
        return Response({
            "valid": False,
            "message": "Invalid QR code format"
        }, status=status.HTTP_400_BAD_REQUEST)

    except EventTicket.DoesNotExist:
        return Response({
            "valid": False,
            "message": "Ticket not found"
        }, status=status.HTTP_404_NOT_FOUND)

    except Exception as e:
        logger.error(f"QR verification error: {str(e)}")
        return Response({
            "valid": False,
            "message": "Verification error"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def checkin_attendee(request, ticket_id):
    """Check in attendee using ticket"""
    ticket = get_object_or_404(
        EventTicket.objects.select_related('registration__event', 'registration__user'),
        id=ticket_id
    )

    # Check permissions
    if (request.user != ticket.registration.event.organizer and
            not request.user.is_staff):
        return Response({
            "success": False,
            "message": "Permission denied"
        }, status=status.HTTP_403_FORBIDDEN)

    if ticket.mark_as_used():
        return Response({
            "success": True,
            "message": f"Successfully checked in {ticket.registration.user.get_full_name()}",
            "attendee_name": ticket.registration.user.get_full_name(),
            "check_in_time": ticket.used_date
        })
    else:
        return Response({
            "success": False,
            "message": "Ticket is not valid for check-in",
            "ticket_status": ticket.status
        }, status=status.HTTP_400_BAD_REQUEST)


class UserRegistrationsView(generics.ListAPIView):
    """Get user's event registrations"""
    serializer_class = EventRegistrationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return EventRegistration.objects.filter(
            user=self.request.user
        ).select_related('event').prefetch_related('ticket').order_by('-registration_date')


class UserTicketsView(generics.ListAPIView):
    """Get user's tickets"""
    serializer_class = EventTicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return EventTicket.objects.filter(
            registration__user=self.request.user,
            status='active'
        ).select_related('registration__event').order_by('-issued_date')


class EventFeaturedView(generics.ListAPIView):
    """List featured events"""
    serializer_class = EventSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        return Event.objects.filter(
            featured=True,
            status='upcoming'
        ).prefetch_related('categories', 'images').order_by('-start_time')


class EventStatsView(APIView):
    """Get event statistics (for organizers)"""
    permission_classes = [IsAuthenticated]

    def get(self, request, event_id):
        event = get_object_or_404(Event, id=event_id, organizer=request.user)

        registrations = event.registrations.all()

        stats = {
            'total_registrations': registrations.count(),
            'confirmed_registrations': event.confirmed_registrations_count,
            'pending_payments': registrations.filter(payment_status='pending').count(),
            'failed_payments': registrations.filter(payment_status='failed').count(),
            'attended': registrations.filter(attended=True).count(),
            'available_spots': event.available_spots,
            'revenue': {
                'total_expected': float(
                    event.price * event.confirmed_registrations_count) if event.event_type == 'paid' else 0,
                'total_collected': float(registrations.filter(payment_status='completed').aggregate(
                    total=models.Sum('amount_paid')
                )['total'] or 0)
            },
            'registrations_by_status': {
                'confirmed': registrations.filter(status='confirmed').count(),
                'pending': registrations.filter(status='pending').count(),
                'canceled': registrations.filter(status='canceled').count(),
                'waitlisted': registrations.filter(status='waitlisted').count(),
            },
            'payment_methods': list(
                registrations.filter(payment_channel__isnull=False)
                .values('payment_channel')
                .annotate(count=models.Count('payment_channel'))
            ) if event.event_type == 'paid' else []
        }

        return Response(stats)


class TechNewsListCreateView(generics.ListCreateAPIView):
    """List and create tech news"""
    serializer_class = TechNewsSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['title', 'content']
    filterset_fields = ['categories', 'news_type', 'is_featured']

    def get_queryset(self):
        return TechNews.objects.filter(
            expiry_date__gte=timezone.now()
        ).select_related('author').prefetch_related('categories').order_by('-published_at')

    def perform_create(self, serializer):
        news = serializer.save(author=self.request.user)
        send_news_notification.delay(news.id)


class NotificationListView(generics.ListAPIView):
    """List user notifications"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.request.user.notifications.order_by('-created_at')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        # Separate read and unread notifications
        unread = queryset.filter(read=False)
        read = queryset.filter(read=True)[:10]  # Limit read notifications

        unread_serializer = self.get_serializer(unread, many=True)
        read_serializer = self.get_serializer(read, many=True)

        return Response({
            'unread_notifications': unread_serializer.data,
            'read_notifications': read_serializer.data,
            'unread_count': unread.count()
        })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        recipient=request.user
    )

    notification.read = True
    notification.save()

    return Response({'success': True, 'message': 'Notification marked as read'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    count = request.user.notifications.filter(read=False).update(read=True)

    return Response({
        'success': True,
        'message': f'{count} notifications marked as read'
    })


# Additional utility views
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_dashboard_stats(request):
    """Get user dashboard statistics"""
    user = request.user

    registrations = EventRegistration.objects.filter(user=user)

    stats = {
        'total_registrations': registrations.count(),
        'upcoming_events': registrations.filter(
            event__start_time__gt=timezone.now(),
            status__in=['confirmed', 'pending']
        ).count(),
        'past_events': registrations.filter(
            event__end_time__lt=timezone.now()
        ).count(),
        'tickets_count': EventTicket.objects.filter(
            registration__user=user,
            status='active'
        ).count(),
        'total_spent': float(registrations.filter(
            payment_status='completed'
        ).aggregate(total=models.Sum('amount_paid'))['total'] or 0),
        'unread_notifications': user.notifications.filter(read=False).count()
    }

    return Response(stats)


@api_view(['GET'])
def payment_methods(request):
    """Get supported payment methods"""
    zenopay = ZenoPayService()
    methods = zenopay.get_supported_payment_methods()

    return Response({
        'payment_methods': methods,
        'currency': 'TZS',
        'supported_countries': ['Tanzania']
    })