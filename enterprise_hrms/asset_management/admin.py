from django.contrib import admin
from .models import (
    AssetCategory, Asset, AssetAssignment,
    AssetMaintenance, SupportTicket, SoftwareLicense,
)


@admin.register(AssetCategory)
class AssetCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'code', 'created_at')
    search_fields = ('name', 'code')
    ordering = ('name',)


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = (
        'asset_code', 'name', 'category', 'serial_number',
        'vendor', 'status', 'purchase_date', 'warranty_expiry_date', 'location',
    )
    search_fields = ('asset_code', 'name', 'serial_number', 'vendor')
    list_filter = ('status', 'category')
    ordering = ('asset_code',)


@admin.register(AssetAssignment)
class AssetAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'asset', 'employee', 'assigned_by',
        'assigned_date', 'expected_return_date', 'actual_return_date', 'status',
    )
    search_fields = (
        'asset__asset_code', 'asset__name',
        'employee__first_name', 'employee__last_name', 'employee__employee_id',
    )
    list_filter = ('status', 'assigned_date')
    ordering = ('-assigned_date',)


@admin.register(AssetMaintenance)
class AssetMaintenanceAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'asset', 'scheduled_by', 'scheduled_date',
        'completed_date', 'status', 'cost',
    )
    search_fields = ('asset__asset_code', 'asset__name', 'description')
    list_filter = ('status', 'scheduled_date')
    ordering = ('-scheduled_date',)


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = (
        'ticket_number', 'employee', 'asset', 'category',
        'priority', 'status', 'assigned_engineer', 'created_at', 'closed_at',
    )
    search_fields = (
        'ticket_number', 'subject', 'description',
        'employee__first_name', 'employee__last_name',
    )
    list_filter = ('status', 'priority', 'category', 'created_at')
    ordering = ('-created_at',)


@admin.register(SoftwareLicense)
class SoftwareLicenseAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'software_name', 'vendor', 'license_type',
        'status', 'assigned_employee', 'purchase_date', 'expiry_date',
    )
    search_fields = ('software_name', 'vendor', 'license_key')
    list_filter = ('status', 'license_type')
    ordering = ('software_name',)
