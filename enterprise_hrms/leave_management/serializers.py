from rest_framework import serializers
from .models import LeaveRequest
from enterprise_hrms.api.validators import validate_leave_dates
from enterprise_hrms.employees.models import Employee

class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    employee_id_code = serializers.ReadOnlyField(source='employee.employee_id')
    manager_name = serializers.SerializerMethodField()
    hr_name = serializers.SerializerMethodField()
    employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all(), required=False)

    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'employee', 'employee_name', 'employee_id_code', 'leave_type', 
            'reason', 'start_date', 'end_date', 'status', 'manager_comments', 
            'hr_comments', 'manager_approved_by', 'manager_name', 'hr_approved_by', 
            'hr_name', 'applied_at', 'updated_at'
        ]
        read_only_fields = [
            'status', 'manager_comments', 'hr_comments', 'manager_approved_by', 
            'hr_approved_by', 'applied_at', 'updated_at'
        ]

    def get_employee_name(self, obj):
        return f"{obj.employee.first_name} {obj.employee.last_name}"

    def get_manager_name(self, obj):
        if obj.manager_approved_by:
            return f"{obj.manager_approved_by.first_name} {obj.manager_approved_by.last_name}"
        return None

    def get_hr_name(self, obj):
        if obj.hr_approved_by:
            return f"{obj.hr_approved_by.first_name} {obj.hr_approved_by.last_name}"
        return None

    def validate(self, attrs):
        start_date = attrs.get('start_date')
        end_date = attrs.get('end_date')
        
        # In case of partial update, retrieve existing values from instance if not in attrs
        if not start_date and self.instance:
            start_date = self.instance.start_date
        if not end_date and self.instance:
            end_date = self.instance.end_date

        try:
            validate_leave_dates(start_date, end_date)
        except Exception as e:
            raise serializers.ValidationError({"end_date": str(e)})

        return attrs
