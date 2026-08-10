from rest_framework import serializers
from enterprise_hrms.employees.models import Employee
from .models import (
    AssetCategory, Asset, AssetAssignment,
    AssetMaintenance, SupportTicket, SoftwareLicense
)
from .validators import (
    validate_warranty_dates,
    validate_license_dates,
)


class AssetCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetCategory
        fields = ['id', 'name', 'code', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class AssetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_code = serializers.CharField(source='category.code', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Asset
        fields = [
            'id', 'asset_code', 'name', 'category', 'category_name', 'category_code',
            'serial_number', 'vendor', 'purchase_date', 'warranty_expiry_date',
            'status', 'status_display', 'location', 'purchase_cost', 'description',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'category_name', 'category_code', 'status_display']

    def validate(self, attrs):
        purchase_date = attrs.get('purchase_date') or (self.instance.purchase_date if self.instance else None)
        warranty_expiry_date = attrs.get('warranty_expiry_date') or (
            self.instance.warranty_expiry_date if self.instance else None
        )
        validate_warranty_dates(purchase_date, warranty_expiry_date)
        return attrs


class AssetAssignmentSerializer(serializers.ModelSerializer):
    asset_code = serializers.CharField(source='asset.asset_code', read_only=True)
    asset_name = serializers.CharField(source='asset.name', read_only=True)
    employee_name = serializers.SerializerMethodField()
    assigned_by_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = AssetAssignment
        fields = [
            'id', 'asset', 'asset_code', 'asset_name',
            'employee', 'employee_name',
            'assigned_by', 'assigned_by_name',
            'assigned_date', 'expected_return_date', 'actual_return_date',
            'status', 'status_display', 'notes',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'status', 'actual_return_date',
            'asset_code', 'asset_name', 'employee_name', 'assigned_by_name',
            'status_display', 'created_at', 'updated_at',
        ]

    def get_employee_name(self, obj):
        return f"{obj.employee.first_name} {obj.employee.last_name}"

    def get_assigned_by_name(self, obj):
        if obj.assigned_by:
            return f"{obj.assigned_by.first_name} {obj.assigned_by.last_name}"
        return None


class AssetAssignRequestSerializer(serializers.Serializer):
    """Serializer for the assign asset action."""
    employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all())
    assigned_date = serializers.DateField(required=False)
    expected_return_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)


class AssetReturnSerializer(serializers.Serializer):
    """Serializer for the return asset action."""
    assignment_id = serializers.IntegerField()
    notes = serializers.CharField(required=False, allow_blank=True)


class AssetMaintenanceSerializer(serializers.ModelSerializer):
    asset_code = serializers.CharField(source='asset.asset_code', read_only=True)
    asset_name = serializers.CharField(source='asset.name', read_only=True)
    scheduled_by_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = AssetMaintenance
        fields = [
            'id', 'asset', 'asset_code', 'asset_name',
            'scheduled_by', 'scheduled_by_name',
            'scheduled_date', 'completed_date',
            'description', 'cost',
            'status', 'status_display',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'asset_code', 'asset_name', 'scheduled_by_name',
            'status_display', 'created_at', 'updated_at',
        ]

    def get_scheduled_by_name(self, obj):
        if obj.scheduled_by:
            return f"{obj.scheduled_by.first_name} {obj.scheduled_by.last_name}"
        return None


class SupportTicketSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    assigned_engineer_name = serializers.SerializerMethodField()
    asset_code = serializers.CharField(source='asset.asset_code', read_only=True, default=None)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = SupportTicket
        fields = [
            'id', 'ticket_number',
            'employee', 'employee_name',
            'asset', 'asset_code',
            'category', 'category_display',
            'priority', 'priority_display',
            'subject', 'description',
            'status', 'status_display',
            'assigned_engineer', 'assigned_engineer_name',
            'resolution_notes',
            'created_at', 'updated_at', 'closed_at',
        ]
        read_only_fields = [
            'id', 'ticket_number',
            'employee_name', 'assigned_engineer_name', 'asset_code',
            'priority_display', 'status_display', 'category_display',
            'closed_at', 'created_at', 'updated_at',
        ]

    def get_employee_name(self, obj):
        return f"{obj.employee.first_name} {obj.employee.last_name}"

    def get_assigned_engineer_name(self, obj):
        if obj.assigned_engineer:
            return f"{obj.assigned_engineer.first_name} {obj.assigned_engineer.last_name}"
        return None

    def validate(self, attrs):
        # On update, check ticket is not closed
        if self.instance and self.instance.status == 'closed':
            from .validators import validate_ticket_not_closed
            validate_ticket_not_closed(self.instance)
        return attrs


class SupportTicketCloseSerializer(serializers.Serializer):
    """Serializer for closing a support ticket."""
    resolution_notes = serializers.CharField(required=False, allow_blank=True)


class SoftwareLicenseSerializer(serializers.ModelSerializer):
    assigned_employee_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    license_type_display = serializers.CharField(source='get_license_type_display', read_only=True)

    class Meta:
        model = SoftwareLicense
        fields = [
            'id', 'software_name', 'license_key', 'vendor',
            'license_type', 'license_type_display',
            'purchase_date', 'expiry_date',
            'assigned_employee', 'assigned_employee_name',
            'status', 'status_display',
            'notes', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'assigned_employee_name', 'status_display',
            'license_type_display', 'created_at', 'updated_at',
        ]

    def get_assigned_employee_name(self, obj):
        if obj.assigned_employee:
            return f"{obj.assigned_employee.first_name} {obj.assigned_employee.last_name}"
        return None

    def validate(self, attrs):
        purchase_date = attrs.get('purchase_date') or (self.instance.purchase_date if self.instance else None)
        expiry_date = attrs.get('expiry_date') or (self.instance.expiry_date if self.instance else None)
        validate_license_dates(purchase_date, expiry_date)
        return attrs


class LicenseAssignSerializer(serializers.Serializer):
    """Serializer for assigning a software license to an employee."""
    employee = serializers.PrimaryKeyRelatedField(queryset=Employee.objects.all())
