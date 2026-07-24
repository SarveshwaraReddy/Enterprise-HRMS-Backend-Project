from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import EmployeeViewSet

router = SimpleRouter()
router.register(r'', EmployeeViewSet, basename='employee')

urlpatterns = [
    path('', include(router.urls)),
]
