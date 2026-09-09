from django.contrib import admin
from .models import Payroll

@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ('employee', 'month', 'year', 'net_salary', 'status', 'generated_at')
    search_fields = ('employee__first_name', 'employee__last_name', 'employee__employee_id')
    list_filter = ('status', 'month', 'year')