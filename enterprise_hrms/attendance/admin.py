from django.contrib import admin

from .models import Attendance


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('employee', 'date', 'check_in', 'check_out', 'status')
    search_fields = ('employee__first_name', 'employee__last_name', 'employee__employee_id', 'date')
    list_filter = ('status', 'date')
