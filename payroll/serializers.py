from rest_framework import serializers
from .models import SalaryStructure, PayrollRun, Payslip, Payroll
from enterprise_hrms.employees.serializers import EmployeeSerializer


class SalaryStructureSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source='employee.__str__', read_only=True)
    gross_salary = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    total_deductions = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    net_salary = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)

    class Meta:
        model = SalaryStructure
        fields = [
            'id', 'employee', 'employee_name', 'basic_salary',
            'house_rent_allowance', 'special_allowance', 'travel_allowance',
            'medical_allowance', 'provident_fund', 'professional_tax',
            'income_tax', 'other_deductions', 'effective_from',
            'status', 'gross_salary', 'total_deductions', 'net_salary',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PayrollRunSerializer(serializers.ModelSerializer):
    processed_by_email = serializers.CharField(source='processed_by.email', read_only=True, default=None)
    approved_by_email = serializers.CharField(source='approved_by.email', read_only=True, default=None)
    total_payslips = serializers.IntegerField(source='payslips.count', read_only=True)

    class Meta:
        model = PayrollRun
        fields = [
            'id', 'payroll_month', 'payroll_year', 'status',
            'processed_by', 'processed_by_email', 'processed_at',
            'approved_by', 'approved_by_email', 'approved_at',
            'remarks', 'total_payslips', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'processed_by', 'processed_at', 'approved_by',
            'approved_at', 'created_at', 'updated_at'
        ]


class PayslipSerializer(serializers.ModelSerializer):
    employee_details = EmployeeSerializer(source='employee', read_only=True)
    employee_id_code = serializers.CharField(source='employee.employee_id', read_only=True)
    employee_name = serializers.CharField(source='employee.__str__', read_only=True)
    department_name = serializers.CharField(source='employee.department.name', read_only=True, default='N/A')
    payroll_month = serializers.IntegerField(source='payroll_run.payroll_month', read_only=True)
    payroll_year = serializers.IntegerField(source='payroll_run.payroll_year', read_only=True)
    payroll_status = serializers.CharField(source='payroll_run.status', read_only=True)

    class Meta:
        model = Payslip
        fields = [
            'id', 'employee', 'employee_id_code', 'employee_name',
            'employee_details', 'department_name', 'payroll_run',
            'payroll_month', 'payroll_year', 'payroll_status',
            'gross_salary', 'total_deductions', 'net_salary',
            'working_days', 'present_days', 'leave_days',
            'overtime_hours', 'pdf_path', 'generated_at'
        ]
        read_only_fields = ['id', 'pdf_path', 'generated_at']


class CreatePayrollRunSerializer(serializers.Serializer):
    payroll_month = serializers.IntegerField(min_value=1, max_value=12)
    payroll_year = serializers.IntegerField(min_value=2000, max_value=2100)
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class PayrollSummaryReportSerializer(serializers.Serializer):
    total_employees_paid = serializers.IntegerField()
    gross_payroll = serializers.DecimalField(max_digits=14, decimal_places=2)
    total_deductions = serializers.DecimalField(max_digits=14, decimal_places=2)
    net_payroll = serializers.DecimalField(max_digits=14, decimal_places=2)


class DepartmentPayrollReportSerializer(serializers.Serializer):
    department_id = serializers.IntegerField()
    department_name = serializers.CharField()
    employee_count = serializers.IntegerField()
    total_payroll = serializers.DecimalField(max_digits=14, decimal_places=2)
    avg_salary = serializers.DecimalField(max_digits=14, decimal_places=2)
    highest_salary = serializers.DecimalField(max_digits=14, decimal_places=2)
    lowest_salary = serializers.DecimalField(max_digits=14, decimal_places=2)


class PayrollSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payroll
        fields = '__all__'
