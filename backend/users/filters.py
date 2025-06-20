import django_filters
from django.db.models import Q
from .models import Hairdresser
import operator
from functools import reduce

class HairdresserFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(
        method='universal_search',
        label="Search by name, city, neighborhood, or resume content"
    )

    class Meta:
        model = Hairdresser
        fields = []

    def universal_search(self, queryset, name, value):
        if not value.strip():
            return queryset
        search_terms = value.split()
        
        search_fields = [
            'user__first_name',
            'user__last_name',
            'user__city',
            'user__address',
            'user__neighborhood',
            'resume',
            'user__preferences__name'
        ]

        # Build a query using Q objects for each search term
        # This creates a series of OR conditions for each term across all fields,
        # and then ANDs the results for each term together.
        # For example, searching "John Manaus" will find hairdressers where
        # ("John" is in any field) AND ("Manaus" is in any field).
        query = reduce(operator.and_,
            (
                reduce(operator.or_, 
                    (Q(**{f'{field}__icontains': term}) for field in search_fields)
                )
                for term in search_terms
            )
        )
        
        return queryset.filter(query).distinct()