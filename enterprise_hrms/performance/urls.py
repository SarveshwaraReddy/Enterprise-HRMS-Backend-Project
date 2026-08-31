from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PerformanceCycleViewSet, GoalViewSet, PerformanceReviewViewSet, ReportsView, AnalyticsView

router = DefaultRouter()
router.register(r'cycles', PerformanceCycleViewSet, basename='performance-cycle')
router.register(r'goals', GoalViewSet, basename='goal')
router.register(r'reviews', PerformanceReviewViewSet, basename='performance-review')

urlpatterns = [
    path('', include(router.urls)),
    path('reports/', ReportsView.as_view(), name='performance-reports'),
    path('analytics/', AnalyticsView.as_view(), name='performance-analytics'),
]
