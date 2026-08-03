from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import AttendanceViewSet

router = SimpleRouter()
router.register(r'', AttendanceViewSet, basename='attendance')

urlpatterns = [
    path('', include(router.urls)),
]
