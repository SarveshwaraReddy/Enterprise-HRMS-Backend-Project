from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import LeaveRequestViewSet

router = SimpleRouter()
router.register(r'', LeaveRequestViewSet, basename='leave')

urlpatterns = [
    path('', include(router.urls)),
]
