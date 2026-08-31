from rest_framework import serializers
from .models import Employee
from enterprise_hrms.departments.models import Department

class DepartmentMinimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ['id', 'name', 'code']

class EmployeeSerializer(serializers.ModelSerializer):
    department_details = DepartmentMinimalSerializer(source='department', read_only=True)
    
    class Meta:
        model = Employee
        fields = [
            'id', 'employee_id', 'first_name', 'last_name', 'email', 'phone',
            'dob', 'gender', 'department', 'department_details', 'designation',
            'salary', 'joining_date', 'status', 'user'
        ]
