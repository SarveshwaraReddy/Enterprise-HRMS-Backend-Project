from rest_framework import serializers
from .models import Attendance
from enterprise_hrms.employees.models import Employee

class AttendanceSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    employee_id_code = serializers.ReadOnlyField(source='employee.employee_id')
    employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all(), required=False)

    class Meta:
        model = Attendance
        fields = ['id', 'employee', 'employee_name', 'employee_id_code', 'date', 'check_in', 'check_out', 'status']

    def get_employee_name(self, obj):
        return f"{obj.employee.first_name} {obj.employee.last_name}"

    def validate(self, attrs):
        # Additional checks can go here
        check_in = attrs.get('check_in')
        check_out = attrs.get('check_out')
        if check_in and check_out and check_in >= check_out:
            raise serializers.ValidationError("Check-out time must be after check-in time.")
        return attrs
