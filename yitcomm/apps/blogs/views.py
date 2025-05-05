from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.contenttypes.models import ContentType
from apps.blogs.filters import BlogFilter
from apps.accounts.models import Bookmark, TechCategory
from .models import Blog, Reaction, Comment
from .serializers import BlogCreateSerializer, BlogSerializer, CategoryWithBlogStatsSerializer, ReactionSerializer, CommentSerializer
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import F, Count

class BlogListCreateAPI(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    queryset = Blog.objects.filter(is_published=True, deleted=False)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class =BlogFilter
    search_fields = ['title', 'content', 'author__username', 'categories__name']
    ordering_fields = ['published_at', 'created_at', 'views']
    ordering = ['-published_at']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return BlogCreateSerializer
        return BlogSerializer
    
    def get_queryset(self):
        queryset = Blog.objects.filter(is_published=True, deleted=False)
        # Filter for bookmarked forums if requested
        bookmarked = self.request.query_params.get('bookmarked')
        if bookmarked and self.request.user.is_authenticated:
            if bookmarked.lower() == 'true':
                # Get content type for Blog model
                blog_content_type = ContentType.objects.get_for_model(Blog)
                # Get IDs of bookmarked blogs
                bookmarked_blogs_ids = Bookmark.objects.filter(
                    user=self.request.user,
                    content_type=blog_content_type
                ).values_list('object_id', flat=True)
                # Filter forums by bookmarked IDs
                queryset = queryset.filter(id__in=bookmarked_blogs_ids)

        return queryset
    
    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

class BlogDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    queryset = Blog.objects.filter(deleted=False)
    serializer_class = BlogSerializer
    lookup_field = 'slug'

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Increment view count using F() to prevent race condition
        Blog.objects.filter(pk=instance.pk).update(views=F('views') + 1)
        instance.refresh_from_db()
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def perform_destroy(self, instance):
        instance.deleted = True
        instance.save()


class BlogReactionView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        blog = generics.get_object_or_404(Blog, pk=pk)
        reaction_type = request.data.get('reaction_type')
        
        # Delete existing reaction if exists
        Reaction.objects.filter(
            user=request.user,
            content_type=ContentType.objects.get_for_model(blog),
            object_id=blog.id
        ).delete()
        
        # Create new reaction if specified
        if reaction_type in dict(Reaction.REACTION_TYPES).keys():
            Reaction.objects.create(
                user=request.user,
                content_object=blog,
                reaction_type=reaction_type
            )
        
        return Response({'status': 'reaction updated'})

class CommentReactionView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        comment = generics.get_object_or_404(Comment, pk=pk)
        reaction_type = request.data.get('reaction_type')
        
        # Update or create reaction
        Reaction.objects.update_or_create(
            user=request.user,
            content_type=ContentType.objects.get_for_model(comment),
            object_id=comment.id,
            defaults={'reaction_type': reaction_type}
        )
        
        return Response({'status': 'reaction updated'})

class CommentCreateView(generics.CreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        content_type = ContentType.objects.get_for_model(Blog)
        serializer.save(
            author=self.request.user,
            content_type=content_type,
            object_id=self.kwargs['blog_id']
        )

class NestedCommentCreateView(generics.CreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        parent_comment = generics.get_object_or_404(Comment, pk=self.kwargs['comment_id'])
        serializer.save(
            author=self.request.user,
            content_type=parent_comment.content_type,
            object_id=parent_comment.object_id,
            parent=parent_comment
        )


class ReactionAPI(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, slug):
        blog = generics.get_object_or_404(Blog, slug=slug)
        reaction_type = request.data.get('reaction_type')
        
        reaction, created = Reaction.objects.update_or_create(
            user=request.user,
            content_type=ContentType.objects.get_for_model(blog),
            object_id=blog.id,
            defaults={'reaction_type': reaction_type}
        )
        
        serializer = ReactionSerializer(reaction)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

class CommentListCreateAPI(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        blog = generics.get_object_or_404(Blog, slug=self.kwargs['slug'])
        return Comment.objects.filter(
            content_type=ContentType.objects.get_for_model(blog),
            object_id=blog.id,
            parent__isnull=True
        )

    def perform_create(self, serializer):
        blog = generics.get_object_or_404(Blog, slug=self.kwargs['slug'])
        serializer.save(
            author=self.request.user,
            content_type=ContentType.objects.get_for_model(blog),
            object_id=blog.id
        )

class CommentRplyListAPI(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        parent_comment = generics.get_object_or_404(Comment, pk=self.kwargs['comment_id'])
        return Comment.objects.filter(
            content_type=parent_comment.content_type,
            object_id=parent_comment.object_id,
            parent=parent_comment
        ).order_by('-created_at')

    def perform_create(self, serializer):
        parent_comment = generics.get_object_or_404(Comment, pk=self.kwargs['comment_id'])
        serializer.save(
            author=self.request.user,
            content_type=parent_comment.content_type,
            object_id=parent_comment.object_id,
            parent=parent_comment
        )
        

class CommentDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    queryset = Comment.objects.all()

    def perform_destroy(self, instance):
        instance.content = "[deleted]"
        instance.author = None
        instance.save()

class BlogsategoriesListView(generics.ListAPIView):
    """
    List all categories that have blogs, with counts of different forum types
    """
    serializer_class = CategoryWithBlogStatsSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        return TechCategory.objects.annotate(
            blogs_count=Count('blog_categories', distinct=True),

        ).filter(blogs_count__gt=0).order_by('-blogs_count', 'name')