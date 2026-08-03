from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SalaryStructureViewSet,
    PayrollRunViewSet,
    PayslipViewSet,
    PayrollDashboardView,
    PayrollReportsView,
    LegacyPayrollViewSet
)

router = DefaultRouter()
router.register(r'salary-structure', SalaryStructureViewSet, basename='salary-structure')
router.register(r'run', PayrollRunViewSet, basename='payroll-run')
router.register(r'payslips', PayslipViewSet, basename='payslip')

urlpatterns = [
    path('dashboard/', PayrollDashboardView.as_view(), name='payroll-dashboard'),
    path('reports/summary/', PayrollReportsView.as_view(), {'report_type': 'summary'}, name='payroll-report-summary'),
    path('reports/department/', PayrollReportsView.as_view(), {'report_type': 'department'}, name='payroll-report-department'),
    path('reports/history/', PayrollReportsView.as_view(), {'report_type': 'history'}, name='payroll-report-history'),
    path('reports/export/', PayrollReportsView.as_view(), {'report_type': 'export'}, name='payroll-report-export'),

    # Explicit legacy route compatibility
    path('generate/', LegacyPayrollViewSet.as_view({'post': 'generate'}), name='legacy-payroll-generate'),
    path('<int:pk>/slip/', LegacyPayrollViewSet.as_view({'get': 'slip'}), name='legacy-payroll-slip'),

    path('', include(router.urls)),
]
