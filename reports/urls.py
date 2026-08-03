from django.urls import path
from .views import EmployeeReportView, DepartmentReportView, AttendanceReportView, PayrollReportView

urlpatterns = [
    path('employees/', EmployeeReportView.as_view(), name='report_employees'),
    path('departments/', DepartmentReportView.as_view(), name='report_departments'),
    path('attendance/', AttendanceReportView.as_view(), name='report_attendance'),
    path('payroll/', PayrollReportView.as_view(), name='report_payroll'),
]
