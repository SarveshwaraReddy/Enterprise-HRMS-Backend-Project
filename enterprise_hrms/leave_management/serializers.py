from rest_framework import serializers
from .models import LeaveType, LeaveBalance, LeaveRequest
from enterprise_hrms.employees.models import Employee


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ['id', 'name', 'code', 'annual_quota', 'is_paid', 'description', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class LeaveBalanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    employee_id_code = serializers.ReadOnlyField(source='employee.employee_id')
    leave_type_name = serializers.ReadOnlyField(source='leave_type.name')
    leave_type_code = serializers.ReadOnlyField(source='leave_type.code')

    class Meta:
        model = LeaveBalance
        fields = [
            'id', 'employee', 'employee_name', 'employee_id_code',
            'leave_type', 'leave_type_name', 'leave_type_code',
            'allocated_days', 'used_days', 'remaining_days', 'year',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['remaining_days', 'created_at', 'updated_at']

    def get_employee_name(self, obj):
        return f"{obj.employee.first_name} {obj.employee.last_name}"


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    employee_id_code = serializers.ReadOnlyField(source='employee.employee_id')
    department_name = serializers.SerializerMethodField()
    leave_type_name = serializers.ReadOnlyField(source='leave_type.name')
    leave_type_code = serializers.ReadOnlyField(source='leave_type.code')
    manager_name = serializers.SerializerMethodField()
    hr_name = serializers.SerializerMethodField()
    employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all(), required=False)
    leave_type = serializers.PrimaryKeyRelatedField(queryset=LeaveType.objects.all())

    class Meta:
        model = LeaveRequest
        fields = [
            'id', 'employee', 'employee_name', 'employee_id_code', 'department_name',
            'leave_type', 'leave_type_name', 'leave_type_code', 'reason',
            'start_date', 'end_date', 'total_days', 'status',
            'manager_comments', 'hr_comments', 'manager_approved_by', 'manager_name',
            'hr_approved_by', 'hr_name', 'applied_at', 'approved_at', 'updated_at'
        ]
        read_only_fields = [
            'total_days', 'status', 'manager_comments', 'hr_comments',
            'manager_approved_by', 'hr_approved_by', 'applied_at', 'approved_at', 'updated_at'
        ]

    def get_employee_name(self, obj):
        return f"{obj.employee.first_name} {obj.employee.last_name}"

    def get_department_name(self, obj):
        return obj.employee.department.name if obj.employee and obj.employee.department else None

    def get_manager_name(self, obj):
        if obj.manager_approved_by:
            return f"{obj.manager_approved_by.first_name} {obj.manager_approved_by.last_name}"
        return None

    def get_hr_name(self, obj):
        if obj.hr_approved_by:
            return f"{obj.hr_approved_by.first_name} {obj.hr_approved_by.last_name}"
        return None


class ApplyLeaveSerializer(serializers.Serializer):
    leave_type = serializers.CharField(help_text="LeaveType ID or Code (e.g. CL, SL, 1)")
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField()
    is_hr_override = serializers.BooleanField(default=False, required=False)


class ApproveRejectSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['approve', 'reject'])
    comments = serializers.CharField(required=False, allow_blank=True, default='')


class CancelLeaveSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default='')
