from django.urls import path
from .views import (
    BlogListCreateAPI,
    BlogDetailAPI,
    ReactionAPI,
    CommentListCreateAPI,
    CommentDetailAPI
)

urlpatterns = [
    path('blogs/', BlogListCreateAPI.as_view(), name='blog-list-create'),
    path('blogs/<slug:slug>/', BlogDetailAPI.as_view(), name='blog-detail'),
    path('blogs/<slug:slug>/reactions/', ReactionAPI.as_view(), name='blog-reactions'),
    path('blogs/<slug:slug>/comments/', CommentListCreateAPI.as_view(), name='blog-comments'),
    path('comments/<int:pk>/', CommentDetailAPI.as_view(), name='comment-detail'),
]