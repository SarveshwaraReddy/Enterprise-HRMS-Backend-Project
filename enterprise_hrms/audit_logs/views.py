from rest_framework import viewsets, mixins
from .models import AuditLog
from .serializers import AuditLogSerializer
from enterprise_hrms.api.permissions import IsAdminOrHR

class AuditLogViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """
    ViewSet to view Audit Logs. Restricted to Admin and HR.
    """
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminOrHR]
    
    # Filter/search configuration
    filterset_fields = ['user', 'action']
    search_fields = ['action', 'description', 'ip_address']
    ordering_fields = ['timestamp']
    ordering = ['-timestamp']
