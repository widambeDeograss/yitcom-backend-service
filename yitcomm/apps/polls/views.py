from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .models import TechPoll, PollVote
from .serializers import TechPollSerializer, PollVoteSerializer
from .permissions import IsAdminOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend

class TechPollListCreateView(generics.ListCreateAPIView):
    serializer_class = TechPollSerializer
    permission_classes = [IsAdminOrReadOnly]
    filterset_fields = ['categories', 'published']
    search_fields = ['title', 'description']
    
    def get_queryset(self):
        return TechPoll.objects.filter(
            published=True
        ).prefetch_related('options', 'categories')
    
    def perform_create(self, serializer):
        if not self.request.user.is_staff:
            raise PermissionDenied("Only admins can create polls")
        serializer.save(created_by=self.request.user)

class TechPollDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TechPoll.objects.all()
    serializer_class = TechPollSerializer
    permission_classes = [IsAdminOrReadOnly]
    
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