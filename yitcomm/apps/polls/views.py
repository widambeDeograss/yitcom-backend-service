from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from .models import TechPoll, PollVote
from .serializers import TechPollSerializer, PollVoteSerializer
from .permissions import IsAdminOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count


class TechPollListCreateView(generics.ListCreateAPIView):
    serializer_class = TechPollSerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['categories', 'published']
    search_fields = ['title', 'description']
    
    def get_queryset(self):
        queryset = TechPoll.objects.filter(
            published=True
        ).prefetch_related(
            'options', 
            'categories',
            'options__votes',
            'votes'
        ).annotate(
            total_votes=Count('votes')
        )
        
        # Annotate each option with its vote count
        for poll in queryset:
            poll.options.all().annotate(vote_count=Count('votes'))
            
        return queryset

    
    def perform_create(self, serializer):
        if not self.request.user.is_staff:
            raise PermissionDenied("Only admins can create polls")
        serializer.save(created_by=self.request.user)

class TechPollDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TechPoll.objects.all()
    serializer_class = TechPollSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = TechPoll.objects.filter(
            published=True
        ).prefetch_related(
            'options', 
            'categories',
            'options__votes',
            'votes'
        ).annotate(
            total_votes=Count('votes')
        )
        
        # Annotate each option with its vote count
        for poll in queryset:
            poll.options.all().annotate(vote_count=Count('votes'))
            
        return queryset
    
    def perform_update(self, serializer):
        if serializer.instance.published:
            raise ValidationError("Published polls cannot be modified")
        super().perform_update(serializer)

class PollVoteCreateView(generics.CreateAPIView):
    serializer_class = PollVoteSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return Response({
            'message': 'Vote recorded successfully',
            'data': response.data
        }, status=status.HTTP_201_CREATED)