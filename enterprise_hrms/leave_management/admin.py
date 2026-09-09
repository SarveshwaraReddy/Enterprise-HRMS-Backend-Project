from django.contrib import admin
from .models import LeaveRequest

@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    list_display = ('employee', 'leave_type', 'start_date', 'end_date', 'status', 'applied_at')
    search_fields = ('employee__first_name', 'employee__last_name', 'employee__employee_id')
    list_filter = ('status', 'leave_type', 'start_date')
    readonly_fields = ('applied_at', 'updated_at')
