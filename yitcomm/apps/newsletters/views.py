from datetime import timezone
from warnings import filters
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db import transaction
from yitcomm.apps.accounts import models
from .models import Newsletter, NewsletterSubscription
from .serializers import NewsletterSerializer, NewsletterSubscriptionSerializer
from yitcomm.apps.accounts.models import TechCategory, User

class NewsletterSubscriptionView(generics.ListCreateAPIView):
    serializer_class = NewsletterSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        """Users can only see their own subscriptions"""
        if self.request.user.is_authenticated:
            return NewsletterSubscription.objects.filter(
                models.Q(user=self.request.user) | 
                models.Q(email=self.request.user.email)
            )
        return NewsletterSubscription.objects.none()

    def perform_create(self, serializer):
        """Link authenticated users automatically"""
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)
        else:
            serializer.save()
            

class SubscriptionPreferencesView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = NewsletterSubscriptionSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    lookup_field = 'email'
    
    def get_queryset(self):
        return NewsletterSubscription.objects.filter(
            models.Q(user=self.request.user) |
            models.Q(email=self.request.user.email)
        )

    def perform_destroy(self, instance):
        """Soft delete by marking inactive"""
        instance.is_active = False
        instance.unsubscribed_at = timezone.now()
        instance.save()

class NewsletterListView(generics.ListAPIView):
    serializer_class = NewsletterSerializer
    queryset = Newsletter.objects.filter(sent_at__isnull=False)
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['title', 'content']
    filterset_fields = ['categories'] 

class NewsletterManagementView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Newsletter.objects.all()
    serializer_class = NewsletterSerializer
    permission_classes = [permissions.IsAdminUser]

class NewsletterSendView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        try:
            newsletter = Newsletter.objects.get(pk=pk, sent_at__isnull=True)
        except Newsletter.DoesNotExist:
            return Response({'error': 'Newsletter not found or already sent'}, 
                          status=status.HTTP_404_NOT_FOUND)

        # Get matching subscribers
        subscribers = NewsletterSubscription.objects.filter(
            is_active=True,
            categories__in=newsletter.categories.all()
        ).distinct()

        # Add sending logic here (use Celery in production)
        # send_newsletter_task.delay(newsletter.id, [s.email for s in subscribers])
        
        newsletter.sent_at = timezone.now()
        newsletter.save()
        
        return Response({
            'message': f'Newsletter queued for {subscribers.count()} subscribers',
            'sent_at': newsletter.sent_at
        }, status=status.HTTP_200_OK)