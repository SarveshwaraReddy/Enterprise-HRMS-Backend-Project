from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import AuditLogViewSet

router = SimpleRouter()
router.register(r'', AuditLogViewSet, basename='audit_log')

urlpatterns = [
    path('', include(router.urls)),
]
