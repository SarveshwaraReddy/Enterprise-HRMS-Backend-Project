from rest_framework import serializers
from .models import Document
from enterprise_hrms.api.validators import validate_file_upload
from enterprise_hrms.employees.models import Employee

class DocumentSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    employee_id_code = serializers.ReadOnlyField(source='employee.employee_id')
    file = serializers.FileField(validators=[validate_file_upload])
    employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all(), required=False)

    class Meta:
        model = Document
        fields = ['id', 'employee', 'employee_name', 'employee_id_code', 'document_type', 'file', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']

    def get_employee_name(self, obj):
        return f"{obj.employee.first_name} {obj.employee.last_name}"
        
    def validate(self, attrs):
        user = self.context['request'].user
        # If employee role, ensure they only upload for themselves
        if user.role == 'employee' and not user.is_superuser:
            try:
                employee = user.employee_profile
                attrs['employee'] = employee
            except Employee.DoesNotExist:
                raise serializers.ValidationError("No employee profile associated with this user.")
        return attrs
