from django.contrib import admin
from .models import SalaryStructure, PayrollRun, Payslip


@admin.register(SalaryStructure)
class SalaryStructureAdmin(admin.ModelAdmin):
    list_display = ('id', 'employee', 'basic_salary', 'gross_salary', 'net_salary', 'effective_from', 'status')
    list_filter = ('status', 'effective_from')
    search_fields = ('employee__first_name', 'employee__last_name', 'employee__employee_id')


@admin.register(PayrollRun)
class PayrollRunAdmin(admin.ModelAdmin):
    list_display = ('id', 'payroll_month', 'payroll_year', 'status', 'processed_by', 'approved_by', 'created_at')
    list_filter = ('status', 'payroll_year', 'payroll_month')
    search_fields = ('remarks',)


@admin.register(Payslip)
class PayslipAdmin(admin.ModelAdmin):
    list_display = ('id', 'employee', 'payroll_run', 'gross_salary', 'total_deductions', 'net_salary', 'generated_at')
    list_filter = ('payroll_run__payroll_year', 'payroll_run__payroll_month', 'payroll_run__status')
    search_fields = ('employee__first_name', 'employee__last_name', 'employee__employee_id')
