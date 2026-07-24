from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import PayrollViewSet

router = SimpleRouter()
router.register(r'', PayrollViewSet, basename='payroll')

urlpatterns = [
    path('', include(router.urls)),
]
