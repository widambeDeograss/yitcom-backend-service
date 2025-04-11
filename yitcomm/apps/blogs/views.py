from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.contenttypes.models import ContentType
from .models import Blog, Reaction, Comment
from .serializers import BlogSerializer, ReactionSerializer, CommentSerializer

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