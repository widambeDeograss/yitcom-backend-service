from django.urls import path
from .views import ProjectListCreateView, ProjectDetailView, ProjectsategoriesListView

urlpatterns = [
    path('', ProjectListCreateView.as_view(), name='project-list-create'),
    path('<int:pk>/', ProjectDetailView.as_view(), name='project-detail'),
    path('categories/', ProjectsategoriesListView.as_view(), name='project-categories'),
]