from django.contrib import admin
from .models import PerformanceCycle, Goal, PerformanceReview

admin.site.register(PerformanceCycle)
admin.site.register(Goal)
admin.site.register(PerformanceReview)
