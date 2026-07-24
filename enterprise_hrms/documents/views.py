import os
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import FileResponse, Http404
from django.conf import settings

from .models import Document
from .serializers import DocumentSerializer
from enterprise_hrms.employees.models import Employee
from enterprise_hrms.api.permissions import IsOwnerOrAdminOrHR
from enterprise_hrms.audit_logs.utils import log_action

class DocumentViewSet(viewsets.ModelViewSet):
    """
    ViewSet to manage employee Documents.
    Supports secure Upload, Download, List, and Delete APIs.
    """
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdminOrHR]
    filterset_fields = ['employee', 'document_type']
    search_fields = ['employee__first_name', 'employee__last_name', 'document_type']
    ordering_fields = ['uploaded_at']
    ordering = ['-uploaded_at']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.role in ['admin', 'hr']:
            return Document.objects.all()
        # Employees can only access their own documents
        try:
            employee = user.employee_profile
            return Document.objects.filter(employee=employee)
        except Employee.DoesNotExist:
            return Document.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if user.role == 'employee' and not user.is_superuser:
            employee = user.employee_profile
            doc = serializer.save(employee=employee)
        else:
            doc = serializer.save()
            
        log_action(
            user=user,
            action="Document Uploaded",
            description=f"Uploaded {doc.get_document_type_display()} for employee {doc.employee.first_name} {doc.employee.last_name}",
            request=self.request
        )

    def perform_destroy(self, instance):
        # Cache file path and name to clean up disk storage
        file_path = instance.file.path
        doc_type = instance.get_document_type_display()
        emp_name = f"{instance.employee.first_name} {instance.employee.last_name}"
        
        # Delete DB instance
        instance.delete()
        
        # Delete file from disk
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
                
        log_action(
            user=self.request.user,
            action="Document Deleted",
            description=f"Deleted {doc_type} for employee {emp_name}",
            request=self.request
        )

    @action(detail=True, methods=['get'], url_path='download')
    def download(self, request, pk=None):
        """
        Secure file download. Reads file from storage and streams to client.
        Enforces IsOwnerOrAdminOrHR permission logic check.
        """
        doc = self.get_object()
        if not doc.file or not os.path.exists(doc.file.path):
            raise Http404("File does not exist on disk.")
            
        # Log download action
        log_action(
            user=request.user,
            action="Document Downloaded",
            description=f"Downloaded document ID {doc.id} ({doc.get_document_type_display()}) for employee {doc.employee.first_name} {doc.employee.last_name}",
            request=request
        )
        
        # Serve file stream securely
        response = FileResponse(open(doc.file.path, 'rb'), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(doc.file.name)}"'
        return response
