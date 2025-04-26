from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response

from apps.accounts.models import Notification
from apps.accounts.serializers import UserSerializer
from .models import Forum, Discussion, Comment, Reaction
from .serializers import CategoryWithForumStatsSerializer, ForumCreateSerializer, ForumSerializer, DiscussionSerializer, CommentSerializer, ReactionSerializer
from .permissions import IsOwnerOrModerator
from django.contrib.contenttypes.models import ContentType
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q
from apps.accounts.models import TechCategory


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


class FollowForumView(generics.CreateAPIView, generics.DestroyAPIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        forum = get_object_or_404(Forum, pk=kwargs['forum_id'])
        if request.user not in forum.followers.all():
            forum.followers.add(request.user)
            forum.followers_count = forum.followers.count()
            forum.save()
            return Response({'status': 'following'}, status=status.HTTP_201_CREATED)
        return Response({'status': 'already following'}, status=status.HTTP_200_OK)
    
    def delete(self, request, *args, **kwargs):
        forum = get_object_or_404(Forum, pk=kwargs['forum_id'])
        if request.user in forum.followers.all():
            forum.followers.remove(request.user)
            forum.followers_count = forum.followers.count()
            forum.save()
            return Response({'status': 'unfollowed'}, status=status.HTTP_200_OK)
        return Response({'status': 'not following'}, status=status.HTTP_200_OK)

class ForumFollowersView(generics.ListAPIView):
    serializer_class = UserSerializer  # You'll need to import your UserSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        forum = get_object_or_404(Forum, pk=self.kwargs['forum_id'])
        return forum.followers.all()

class DiscussionListCreateView(generics.ListCreateAPIView):
    serializer_class = DiscussionSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def perform_create(self, serializer):
        discussion = serializer.save(author=self.request.user)
        forum = discussion.forum
        
        # Notify all followers of the forum
        if forum.followers.exists():
            notifications = [
                Notification(
                    user=follower,
                    notification_type='new_discussion',
                    title=f"New discussion in {forum.title}",
                    message=f"{self.request.user.username} started a new discussion: {discussion.title}",
                    content_type=ContentType.objects.get_for_model(discussion),
                    object_id=discussion.id
                )
                for follower in forum.followers.exclude(id=self.request.user.id)
            ]
            Notification.objects.bulk_create(notifications)

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


class ForumCategoriesListView(generics.ListAPIView):
    """
    List all categories that have forums, with counts of different forum types
    """
    serializer_class = CategoryWithForumStatsSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        return TechCategory.objects.annotate(
            forum_count=Count('forums', distinct=True),
            active_forum_count=Count(
                'forums', 
                distinct=True, 
                filter=Q(forums__is_active=True)
            ),
            public_forum_count=Count(
                'forums', 
                distinct=True, 
                filter=Q(forums__is_public=True)
            )
        ).filter(forum_count__gt=0).order_by('-forum_count', 'name')