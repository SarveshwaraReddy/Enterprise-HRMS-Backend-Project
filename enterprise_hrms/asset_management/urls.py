from django.urls import path, include
from rest_framework.routers import SimpleRouter
from .views import (
    AssetCategoryViewSet,
    AssetViewSet,
    AssetAssignmentViewSet,
    AssetMaintenanceViewSet,
    SupportTicketViewSet,
    SoftwareLicenseViewSet,
    AssetDashboardView,
    AssetReportView,
)

router = SimpleRouter()

# Register specific prefixes BEFORE the empty-prefix AssetViewSet
# so Django URL resolution matches them first.
router.register(r'categories', AssetCategoryViewSet, basename='asset-category')
router.register(r'assignments', AssetAssignmentViewSet, basename='asset-assignment')
router.register(r'maintenance', AssetMaintenanceViewSet, basename='asset-maintenance')
router.register(r'support/tickets', SupportTicketViewSet, basename='support-ticket')
router.register(r'licenses', SoftwareLicenseViewSet, basename='software-license')

# Asset ViewSet at empty prefix – generates the following endpoints:
#   GET/POST /api/v1/assets/
#   GET/PUT/PATCH/DELETE /api/v1/assets/{id}/
#   POST /api/v1/assets/assign/
#   PUT  /api/v1/assets/return/
#   GET  /api/v1/assets/my-assets/
#   GET  /api/v1/assets/summary/
#   POST /api/v1/assets/{id}/schedule-maintenance/
router.register(r'', AssetViewSet, basename='asset')

urlpatterns = [
    # Dashboard – GET /api/v1/assets/dashboard/
    path('dashboard/', AssetDashboardView.as_view(), name='asset-dashboard'),

    # Reports – GET /api/v1/assets/reports/<type>/?format=pdf|excel|csv
    path('reports/assets/', AssetReportView.as_view(), {'report_type': 'assets'}, name='report-assets'),
    path('reports/support/', AssetReportView.as_view(), {'report_type': 'support'}, name='report-support'),
    path('reports/licenses/', AssetReportView.as_view(), {'report_type': 'licenses'}, name='report-licenses'),

    # All router-generated URLs (specific prefixes + catch-all Asset prefix)
    path('', include(router.urls)),
]
