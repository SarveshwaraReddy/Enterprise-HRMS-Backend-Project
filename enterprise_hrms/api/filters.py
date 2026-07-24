from rest_framework import filters
from django_filters import rest_framework as django_filters

class CustomFilterBackend(django_filters.DjangoFilterBackend):
    """
    Base filter backend mapping django-filter settings to standard parameters.
    """
    pass
