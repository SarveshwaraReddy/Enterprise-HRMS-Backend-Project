from rest_framework import permissions
from enterprise_hrms.employees.models import Employee


class IsLeaveOwnerOrManagerOrHR(permissions.BasePermission):
    """
    Permission check:
    - Admin or HR has full access.
    - Department Manager has access to leave requests of employees in their department.
    - Employee has access to their own leave requests.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser or getattr(user, 'role', '') in ['admin', 'hr']:
            return True

        try:
            employee = user.employee_profile
        except Employee.DoesNotExist:
            return False

        # Owner check
        if getattr(obj, 'employee', None) == employee:
            return True

        # Manager check
        req_employee = getattr(obj, 'employee', None)
        if req_employee and req_employee.department and req_employee.department.manager == employee:
            return True

        return False


class IsDepartmentManager(permissions.BasePermission):
    """
    Permission check for department manager actions.
    """
    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_superuser or getattr(user, 'role', '') in ['admin', 'hr']:
            return True
        try:
            employee = user.employee_profile
            return employee.managed_departments.exists()
        except Employee.DoesNotExist:
            return False


class IsHROrAdmin(permissions.BasePermission):
    """
    Permission check strictly for HR or Admin users.
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            (request.user.is_superuser or getattr(request.user, 'role', '') in ['admin', 'hr'])
        )
