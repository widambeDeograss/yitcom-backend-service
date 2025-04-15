import django_filters
from .models import Blog
from apps.accounts.models import User, TechCategory

class BlogFilter(django_filters.FilterSet):
    title = django_filters.CharFilter(lookup_expr='icontains')
    author = django_filters.ModelChoiceFilter(queryset=User.objects.all())
    categories = django_filters.ModelMultipleChoiceFilter(
        queryset=TechCategory.objects.all(),
        field_name='categories__name',
        lookup_expr='iexact'
    )
    published_after = django_filters.DateFilter(
        field_name='published_at',
        lookup_expr='gte'
    )
    published_before = django_filters.DateFilter(
        field_name='published_at',
        lookup_expr='lte'
    )
    is_published = django_filters.BooleanFilter()
    draft = django_filters.BooleanFilter()

    class Meta:
        model = Blog
        fields = ['title', 'author', 'categories', 'is_published', 'draft']