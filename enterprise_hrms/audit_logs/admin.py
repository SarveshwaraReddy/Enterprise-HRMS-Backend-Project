from django.contrib import admin
from .models import AuditLog

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'module', 'model_name')
    search_fields = ('user__username', 'action', 'module', 'model_name', 'ip_address')
    list_filter = ('action', 'module', 'timestamp')
    readonly_fields = ('timestamp', 'user', 'action', 'description', 'module', 'model_name', 'object_id', 'old_data', 'new_data', 'ip_address', 'user_agent', 'request_id')

    def has_add_permission(self, request):
        return False
        
    def has_change_permission(self, request, obj=None):
        return False
