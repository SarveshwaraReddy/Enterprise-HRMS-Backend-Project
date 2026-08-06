from django.contrib import admin
from django.contrib.auth import get_user_model

from enterprise_hrms.accounts.models import User
from enterprise_hrms.attendance.models import Attendance
from enterprise_hrms.audit_logs.models import AuditLog
from enterprise_hrms.departments.models import Department
from enterprise_hrms.documents.models import Document
from enterprise_hrms.employees.models import Employee
from enterprise_hrms.notifications.models import Notification
from enterprise_hrms.payroll.models import Payroll
from .models import LeaveType, LeaveBalance, LeaveRequest


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'code', 'annual_quota', 'is_paid', 'created_at')
    search_fields = ('name', 'code')
    list_filter = ('is_paid',)


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display = ('id', 'employee', 'leave_type', 'allocated_days', 'used_days', 'remaining_days', 'year')
    search_fields = ('employee__first_name', 'employee__last_name', 'employee__employee_id', 'leave_type__code')
    list_filter = ('year', 'leave_type')


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'employee', 'leave_type', 'start_date', 'end_date', 'total_days', 'status', 'applied_at')
    search_fields = ('employee__first_name', 'employee__last_name', 'employee__employee_id', 'reason')
    list_filter = ('status', 'leave_type', 'start_date')


@admin.register(get_user_model())
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'username', 'role', 'is_staff', 'is_active')
    search_fields = ('email', 'username', 'phone')
    list_filter = ('role', 'is_staff', 'is_active')


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('employee_id', 'first_name', 'last_name', 'email', 'department', 'designation', 'status')
    search_fields = ('employee_id', 'first_name', 'last_name', 'email')
    list_filter = ('status', 'department', 'gender')


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'manager')
    search_fields = ('name', 'code')


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'check_in', 'check_out', 'status')
    search_fields = ('employee__employee_id', 'employee__first_name', 'employee__last_name')
    list_filter = ('status', 'date')


@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ('employee', 'month', 'year', 'basic_salary', 'allowances', 'deductions', 'net_salary', 'status')
    search_fields = ('employee__employee_id', 'employee__first_name', 'employee__last_name')
    list_filter = ('status', 'year', 'month')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('employee', 'document_type', 'file', 'uploaded_at')
    search_fields = ('employee__employee_id', 'employee__first_name', 'employee__last_name')
    list_filter = ('document_type', 'uploaded_at')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'title', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'recipient__email')
    list_filter = ('is_read', 'created_at')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'action', 'ip_address', 'timestamp')
    search_fields = ('action', 'description', 'user__email')
    list_filter = ('timestamp', 'action')
