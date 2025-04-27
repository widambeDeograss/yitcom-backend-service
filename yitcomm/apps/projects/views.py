from rest_framework import generics, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend

from apps.accounts.models import TechCategory
from .models import Project
from .serializers import CategoryWithProjectStatsSerializer, ProjectSerializer
from .permissions import IsOwnerOrReadOnly
from django.db.models import Q, Count

class ProjectListCreateView(generics.ListCreateAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['categories', 'technologies_used']
    search_fields = ['title', 'description', 'author__username']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter projects based on publication state and user"""
        queryset = super().get_queryset()
        user = self.request.user

        # For authenticated users: show their drafts + published projects
        if user.is_authenticated:
            return queryset.filter(
                models.Q(published=True) |
                models.Q(drafted=True, author=user)
            )
        # For anonymous users: only published projects
        return queryset.filter(published=True)


class ProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]

    def get_queryset(self):
        return Project.objects.prefetch_related(
            'categories', 'technologies_used', 'contributors'
        ).select_related('author')
    

class ProjectsategoriesListView(generics.ListAPIView):
    """
    List all categories that have projects, with counts of different forum types
    """
    serializer_class = CategoryWithProjectStatsSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        return TechCategory.objects.annotate(
            project_count=Count('projects', distinct=True),

        ).filter(project_count__gt=0).order_by('-project_count', 'name')
    