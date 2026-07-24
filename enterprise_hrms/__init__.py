import datetime

from django.utils import timezone as django_timezone

if not hasattr(django_timezone, "utc"):
    django_timezone.utc = datetime.timezone.utc
