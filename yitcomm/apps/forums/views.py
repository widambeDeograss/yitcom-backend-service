from rest_framework import generics, permissions, status
from rest_framework.response import Response
from .models import Forum, Discussion, Comment, Reaction
from .serializers import ForumCreateSerializer, ForumSerializer, DiscussionSerializer, CommentSerializer, ReactionSerializer
from .permissions import IsOwnerOrModerator
from django.contrib.contenttypes.models import ContentType

class ForumListCreateView(generics.ListCreateAPIView):
    serializer_class = ForumSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_serializer_class(self):
        return ForumCreateSerializer if self.request.method == 'POST' else ForumSerializer
    
    def get_queryset(self):
        return Forum.objects.filter(is_public=True).select_related('category', 'created_by')

class ForumDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Forum.objects.all()
    serializer_class = ForumSerializer
    permission_classes = [IsOwnerOrModerator]

class DiscussionListCreateView(generics.ListCreateAPIView):
    serializer_class = DiscussionSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_queryset(self):
        return Discussion.objects.filter(
            forum_id=self.kwargs['forum_id'],
            forum__is_public=True
        ).select_related('author', 'forum')

class DiscussionDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DiscussionSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        return Discussion.objects.select_related('author', 'forum')

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.views += 1
        instance.save()
        return super().retrieve(request, *args, **kwargs)

class ReactionView(generics.CreateAPIView, generics.DestroyAPIView):
    serializer_class = ReactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def create(self, request, *args, **kwargs):
        content_type = ContentType.objects.get_for_model(self.get_content_object())
        serializer = self.get_serializer(data={
            'reaction': request.data['reaction'],
            'content_type': content_type.id,
            'object_id': self.kwargs['object_id']
        })
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    def get_content_object(self):
        model = self.kwargs['content_type']
        obj_id = self.kwargs['object_id']
        return model.objects.get(pk=obj_id)