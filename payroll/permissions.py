from rest_framework import permissions


class IsHR(permissions.BasePermission):
    """
    Allows access only to HR users or Superusers.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.role == 'hr' or request.user.is_superuser)
        )


class IsPayrollAdmin(permissions.BasePermission):
    """
    Allows access to Admin, HR users, or Superusers.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.role in ['admin', 'hr'] or request.user.is_superuser)
        )


class IsEmployee(permissions.BasePermission):
    """
    Allows access only to Employee users.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (request.user.role == 'employee')
        )


class IsPayslipOwnerOrAdmin(permissions.BasePermission):
    """
    Allows access to object if user is Admin/HR, or if the payslip belongs to the request user's Employee profile.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser or request.user.role in ['admin', 'hr']:
            return True
        if hasattr(obj, 'employee') and obj.employee:
            return bool(obj.employee.user == request.user)
        return False
