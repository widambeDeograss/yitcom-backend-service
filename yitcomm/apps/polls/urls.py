from django.urls import path
from .views import (
    TechPollListCreateView,
    TechPollDetailView,
    PollVoteCreateView
)

urlpatterns = [
    path('polls/', TechPollListCreateView.as_view(), name='poll-list'),
    path('polls/<int:pk>/', TechPollDetailView.as_view(), name='poll-detail'),
    path('votes/', PollVoteCreateView.as_view(), name='vote-create'),
]