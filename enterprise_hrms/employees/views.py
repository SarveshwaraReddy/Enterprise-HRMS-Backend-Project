from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import Employee
from .serializers import EmployeeSerializer
from enterprise_hrms.api.permissions import IsOwnerOrAdminOrHR, IsAdminOrHR
from .services import EmployeeService

class EmployeeViewSet(viewsets.ModelViewSet):
    """
    ViewSet to manage employee profiles.
    Admin/HR have full access. Employees can only view/retrieve their own profile.
    """
    serializer_class = EmployeeSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdminOrHR]
    filterset_fields = ['department', 'gender', 'status']
    search_fields = ['first_name', 'last_name', 'email', 'employee_id']
    ordering_fields = ['joining_date', 'employee_id']
    ordering = ['employee_id']

    def get_queryset(self):
        user = self.request.user
        queryset = Employee.objects.select_related('department', 'user')
        if user.is_superuser or user.role in ['admin', 'hr']:
            return queryset.all()
        # Employees can only access their own profile
        try:
            return queryset.filter(user=user)
        except Exception:
            return Employee.objects.none()

    def create(self, request, *args, **kwargs):
        # Only Admin or HR can create employees
        if not (request.user.is_superuser or request.user.role in ['admin', 'hr']):
            return Response(
                {"success": False, "message": "Only Admin or HR can register new employees."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        # Only Admin or HR can delete employees
        if not (request.user.is_superuser or request.user.role in ['admin', 'hr']):
            return Response(
                {"success": False, "message": "Only Admin or HR can delete employees."},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)

    def perform_create(self, serializer):
        EmployeeService.create_employee(serializer, self.request)

    def perform_update(self, serializer):
        EmployeeService.update_employee(serializer, self.request)

    def perform_destroy(self, instance):
        EmployeeService.delete_employee(instance, self.request)