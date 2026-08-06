from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import LeaveTypeViewSet, LeaveBalanceViewSet, LeaveRequestViewSet

router = SimpleRouter()
router.register(r'types', LeaveTypeViewSet, basename='leave-type')
router.register(r'balances', LeaveBalanceViewSet, basename='leave-balance')
router.register(r'', LeaveRequestViewSet, basename='leave')

urlpatterns = [
    path('', include(router.urls)),
]
