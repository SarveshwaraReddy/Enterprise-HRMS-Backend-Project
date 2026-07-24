from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import DocumentViewSet

router = SimpleRouter()
router.register(r'', DocumentViewSet, basename='document')

urlpatterns = [
    path('', include(router.urls)),
]
