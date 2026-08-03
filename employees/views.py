from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from .models import Employee
from .serializers import EmployeeSerializer
from enterprise_hrms.api.permissions import IsOwnerOrAdminOrHR, IsAdminOrHR
from enterprise_hrms.audit_logs.utils import log_action

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
        if user.is_superuser or user.role in ['admin', 'hr']:
            return Employee.objects.all()
        # Employees can only access their own profile
        try:
            return Employee.objects.filter(user=user)
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
        emp = serializer.save()
        log_action(
            user=self.request.user,
            action="Employee Created",
            description=f"Registered employee: {emp.first_name} {emp.last_name} ({emp.employee_id})",
            request=self.request
        )

    def perform_update(self, serializer):
        emp = serializer.save()
        log_action(
            user=self.request.user,
            action="Employee Updated",
            description=f"Updated employee: {emp.first_name} {emp.last_name} ({emp.employee_id})",
            request=self.request
        )

    def perform_destroy(self, instance):
        emp_name = f"{instance.first_name} {instance.last_name}"
        emp_id = instance.employee_id
        instance.delete()
        log_action(
            user=self.request.user,
            action="Employee Deleted",
            description=f"Deleted employee: {emp_name} ({emp_id})",
            request=self.request
        )