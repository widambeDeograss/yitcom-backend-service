from django.urls import path
from .views import (
    CheckForumFollowStatus,
    FollowForumView,
    ForumCategoriesListView,
    ForumFollowersView,
    ForumListCreateView,
    ForumDetailView,
    DiscussionListCreateView,
    DiscussionDetailView,
    ReactionView
)

urlpatterns = [
    path('forums/', ForumListCreateView.as_view(), name='forum-list'),
    path('forums/<int:pk>/', ForumDetailView.as_view(), name='forum-detail'),
    path('forums/<int:forum_id>/discussions/', DiscussionListCreateView.as_view(), name='discussion-list'),
    path('discussions/<int:pk>/', DiscussionDetailView.as_view(), name='discussion-detail'),
    path('reactions/<str:content_type>/<int:object_id>/', ReactionView.as_view(), name='reaction'),
    path('forums/<int:forum_id>/follow/', FollowForumView.as_view(), name='forum-follow'),
    path('forums/<int:forum_id>/followers/', ForumFollowersView.as_view(), name='forum-followers'),
    path('forum-categories/', ForumCategoriesListView.as_view(), name='forum-categories-list'),
    path('forums/<int:forum_id>/check-follow/', CheckForumFollowStatus.as_view(), name='check-forum-follow'),
]