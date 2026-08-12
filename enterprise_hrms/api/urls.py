from django.urls import path, include

urlpatterns = [
    path('auth/', include('enterprise_hrms.accounts.urls')),
    path('employees/', include('enterprise_hrms.employees.urls')),
    path('departments/', include('enterprise_hrms.departments.urls')),
    path('attendance/', include('enterprise_hrms.attendance.urls')),
    path('leaves/', include('enterprise_hrms.leave_management.urls')),
    path('payroll/', include('enterprise_hrms.payroll.urls')),
    path('documents/', include('enterprise_hrms.documents.urls')),
    path('reports/', include('enterprise_hrms.reports.urls')),
    path('dashboard/', include('enterprise_hrms.dashboard.urls')),
    path('audit-logs/', include('enterprise_hrms.audit_logs.urls')),
    path('notifications/', include('enterprise_hrms.notifications.urls')),
    path('assets/', include('enterprise_hrms.asset_management.urls')),
    path('performance/', include('enterprise_hrms.performance.urls')),
]