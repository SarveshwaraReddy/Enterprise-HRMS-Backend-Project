from rest_framework import serializers
from .models import Payroll
from enterprise_hrms.employees.models import Employee

class PayrollSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    employee_id_code = serializers.ReadOnlyField(source='employee.employee_id')

    class Meta:
        model = Payroll
        fields = [
            'id', 'employee', 'employee_name', 'employee_id_code', 'month', 'year', 
            'basic_salary', 'allowances', 'deductions', 'net_salary', 'status', 
            'generated_at', 'paid_at'
        ]
        read_only_fields = ['id', 'net_salary', 'generated_at']

    def get_employee_name(self, obj):
        return f"{obj.employee.first_name} {obj.employee.last_name}"

    def validate(self, attrs):
        basic_salary = attrs.get('basic_salary')
        allowances = attrs.get('allowances', 0)
        deductions = attrs.get('deductions', 0)
        
        if basic_salary is not None and basic_salary <= 0:
            raise serializers.ValidationError({"basic_salary": "Basic salary must be greater than zero."})
            
        if allowances < 0:
            raise serializers.ValidationError({"allowances": "Allowances cannot be negative."})
            
        if deductions < 0:
            raise serializers.ValidationError({"deductions": "Deductions cannot be negative."})
            
        return attrs
