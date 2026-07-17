import django_filters
from django.db import connection
from django.db.models import Q
from .models import Task


class TaskFilter(django_filters.FilterSet):
    due_date_after = django_filters.DateTimeFilter(field_name='due_date', lookup_expr='gte')
    due_date_before = django_filters.DateTimeFilter(field_name='due_date', lookup_expr='lte')
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = Task
        fields = ['status', 'priority', 'project']

    def filter_search(self, queryset, name, value):
        if connection.vendor == 'postgresql':
            from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
            vector = SearchVector('title', weight='A') + SearchVector('description', weight='B')
            query = SearchQuery(value)
            return queryset.annotate(rank=SearchRank(vector, query)).filter(rank__gt=0).order_by('-rank')

        # SQLite fallback for local dev — no real full-text ranking available
        return queryset.filter(Q(title__icontains=value) | Q(description__icontains=value))
