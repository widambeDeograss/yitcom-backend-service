from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response

from apps.accounts.models import Bookmark, Notification
from apps.accounts.serializers import UserSerializer
from .models import Forum, Discussion, Comment, Reaction
from .serializers import CategoryWithForumStatsSerializer, DiscussionCreateSerializer, ForumCreateSerializer, ForumSerializer, DiscussionSerializer, CommentSerializer, ReactionSerializer
from .permissions import IsOwnerOrModerator
from django.contrib.contenttypes.models import ContentType
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Q
from apps.accounts.models import TechCategory


class ForumListCreateView(generics.ListCreateAPIView):
    serializer_class = ForumSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['category', 'is_active', 'is_public', 'followers']  # Added 'followers'
    search_fields = ['title', 'description', 'category__name']
    
    def get_serializer_class(self):
        return ForumCreateSerializer if self.request.method == 'POST' else ForumSerializer
    
    def get_queryset(self):
        queryset = Forum.objects.filter(is_public=True).annotate(
            discussion_count=Count('discussions', distinct=True)
        ).select_related('category', 'created_by')

        # Filter for followed forums if requested
        followed_by = self.request.query_params.get('followed_by')
        if followed_by:
            if followed_by == 'me':
                queryset = queryset.filter(followers=self.request.user)
            else:
                try:
                    user_id = int(followed_by)
                    queryset = queryset.filter(followers__id=user_id)
                except (ValueError, TypeError):
                    pass
        
        # Filter for bookmarked forums if requested
        bookmarked = self.request.query_params.get('bookmarked')
        if bookmarked and self.request.user.is_authenticated:
            if bookmarked.lower() == 'true':
                # Get content type for Forum model
                forum_content_type = ContentType.objects.get_for_model(Forum)
                # Get IDs of bookmarked forums
                bookmarked_forum_ids = Bookmark.objects.filter(
                    user=self.request.user,
                    content_type=forum_content_type
                ).values_list('object_id', flat=True)
                # Filter forums by bookmarked IDs
                queryset = queryset.filter(id__in=bookmarked_forum_ids)

    

        # Increment views if a single forum is being retrieved
        if self.request.query_params.get('id'):
            forum_id = self.request.query_params.get('id')
            forum = queryset.filter(id=forum_id).first()
            if forum:
                forum.increment_views()

        return queryset
    
    
class ForumDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Forum.objects.all()
    serializer_class = ForumSerializer
    permission_classes = [IsOwnerOrModerator]

    def get_queryset(self):
        return Forum.objects.annotate(
            discussion_count=Count('discussions')
        )


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

    def get_serializer_class(self):
        return DiscussionCreateSerializer  if self.request.method == 'POST' else DiscussionSerializer
    
    def perform_create(self, serializer):
        discussion = serializer.save(author=self.request.user)
        forum = discussion.forum
        
        # Notify all followers of the forum
        if forum.followers.exists():
            content_type = ContentType.objects.get_for_model(discussion)
            notifications = [
                Notification(
                    user=follower,
                    notification_type='new_discussion',
                    title=f"New discussion in {forum.title}",
                    message=f"{self.request.user.username} started a new discussion: {discussion.title}",
                    content_type=content_type,
                    object_id=discussion.id
                )
                for follower in forum.followers.exclude(id=self.request.user.id)
            ]
            Notification.objects.bulk_create(notifications)

    def get_queryset(self):
        return Discussion.objects.with_reactions().filter(
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
    
    # Model mapping for content types
    CONTENT_TYPE_MAP = {
        'discussion': Discussion,
        'comment': Comment,
        # Add other content types as needed
    }

    def get_content_object(self):
        """Get the content object being reacted to"""
        content_type = self.kwargs.get('content_type')  # 'discussion' or 'comment'
        object_id = self.kwargs.get('object_id')
        
        model_class = self.CONTENT_TYPE_MAP.get(content_type)
        if not model_class:
            raise ValueError(f"Invalid content type: {content_type}. Valid options are: {', '.join(self.CONTENT_TYPE_MAP.keys())}")
            
        try:
            return model_class.objects.get(pk=object_id)
        except model_class.DoesNotExist:
            raise ValueError(f"{content_type} with id {object_id} does not exist")

    def post(self, request, *args, **kwargs):
        """Handle creating or updating a reaction"""
        try:
            content_object = self.get_content_object()
            content_type = ContentType.objects.get_for_model(content_object)
            reaction_type = request.data.get('reaction')
            
            if not reaction_type:
                return Response(
                    {"detail": "Reaction type is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Validate reaction type
            if reaction_type not in dict(Reaction.REACTION_CHOICES):
                return Response(
                    {"detail": f"Invalid reaction type. Valid choices are: {dict(Reaction.REACTION_CHOICES)}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check for existing reaction
            existing_reaction, created = Reaction.objects.get_or_create(
                user=request.user,
                content_type=content_type,
                object_id=content_object.id,
                defaults={'reaction': reaction_type}
            )
            
            if not created:
                if existing_reaction.reaction == reaction_type:
                    # Same reaction - remove it
                    existing_reaction.delete()
                    self.update_reaction_count(content_object, increment=False)
                    return Response(
                        {"detail": "Reaction removed", "action": "removed"},
                        status=status.HTTP_200_OK
                    )
                else:
                    # Different reaction - update it
                    existing_reaction.reaction = reaction_type
                    existing_reaction.save()
                    action = "changed"
            else:
                action = "added"
                self.update_reaction_count(content_object, increment=True)
            
            serializer = self.get_serializer(existing_reaction)
            return Response(
                {
                    **serializer.data,
                    "action": action,
                    "content_type": content_type.model,
                    "object_id": content_object.id
                },
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
            )
            
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"detail": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def delete(self, request, *args, **kwargs):
        """Handle removing a reaction"""
        try:
            content_object = self.get_content_object()
            content_type = ContentType.objects.get_for_model(content_object)
            
            reaction = Reaction.objects.filter(
                user=request.user,
                content_type=content_type,
                object_id=content_object.id
            ).first()
            
            if not reaction:
                return Response(
                    {"detail": "No reaction found to remove"},
                    status=status.HTTP_404_NOT_FOUND
                )
                
            self.update_reaction_count(content_object, increment=False)
            reaction.delete()
            
            return Response(
                {"detail": "Reaction removed", "action": "removed"},
                status=status.HTTP_204_NO_CONTENT
            )
            
        except ValueError as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"detail": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update_reaction_count(self, content_object, increment=True):
        """Update reaction count on the content object if it has such field"""
        if hasattr(content_object, 'reactions_count'):
            if increment:
                content_object.reactions_count += 1
            else:
                content_object.reactions_count = max(0, content_object.reactions_count - 1)
            content_object.save(update_fields=['reactions_count'])



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
    

class CheckForumFollowStatus(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        forum_id = self.kwargs.get('forum_id')
        try:
            forum = Forum.objects.get(pk=forum_id)
            is_following = request.user in forum.followers.all()
            return Response({
                'is_following': is_following,
                'forum_id': forum_id,
                'user_id': request.user.id
            }, status=status.HTTP_200_OK)
        except Forum.DoesNotExist:
            return Response(
                {'detail': 'Forum not found'},
                status=status.HTTP_404_NOT_FOUND
            )   