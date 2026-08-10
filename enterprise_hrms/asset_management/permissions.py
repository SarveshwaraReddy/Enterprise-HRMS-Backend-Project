from rest_framework import permissions
from enterprise_hrms.employees.models import Employee


class IsITTeamOrAdmin(permissions.BasePermission):
    """
    Allows access only to users with 'it' or 'admin' role.
    Used for asset management operations (create, assign, maintain).
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            (request.user.is_superuser or getattr(request.user, 'role', '') in ['admin', 'it'])
        )


class IsHROrAdmin(permissions.BasePermission):
    """
    Allows access only to users with 'hr' or 'admin' role.
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            (request.user.is_superuser or getattr(request.user, 'role', '') in ['admin', 'hr'])
        )


class IsITOrHROrAdmin(permissions.BasePermission):
    """
    Allows access to IT team, HR, or Admin users.
    Used for report generation and dashboard access.
    """
    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            (
                request.user.is_superuser or
                getattr(request.user, 'role', '') in ['admin', 'hr', 'it']
            )
        )


class IsTicketOwnerOrITOrAdmin(permissions.BasePermission):
    """
    - Admin / IT team: full access.
    - Employee: access only to their own tickets (read or create).
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser or getattr(user, 'role', '') in ['admin', 'it']:
            return True
        try:
            employee = user.employee_profile
        except Employee.DoesNotExist:
            return False
        return getattr(obj, 'employee', None) == employee


class IsAssetAssigneeOrITOrAdmin(permissions.BasePermission):
    """
    - Admin / IT team: full access to assignments.
    - Employee: can view only their own assignments.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser or getattr(user, 'role', '') in ['admin', 'it']:
            return True
        try:
            employee = user.employee_profile
        except Employee.DoesNotExist:
            return False
        return getattr(obj, 'employee', None) == employee
