from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import DepartmentViewSet

router = SimpleRouter()
router.register(r'', DepartmentViewSet, basename='department')

urlpatterns = [
    path('', include(router.urls)),
]
