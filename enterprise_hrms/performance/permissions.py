from rest_framework import permissions

class IsHR(permissions.BasePermission):
    """
    Allows access only to HR users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and getattr(request.user, 'role', '') == 'HR')

class IsManager(permissions.BasePermission):
    """
    Allows access only to Manager users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and getattr(request.user, 'role', '') == 'Manager')

class IsOwnerOrHR(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object or HR to view/edit it.
    Assumes the model has an `employee.user` attribute.
    """
    def has_object_permission(self, request, view, obj):
        if getattr(request.user, 'role', '') == 'HR':
            return True
        return hasattr(obj, 'employee') and obj.employee.user == request.user

class IsManagerOfEmployee(permissions.BasePermission):
    """
    Custom permission to allow a manager to edit/view if they manage the employee.
    Assumes employee has a `manager` attribute linked to another employee object which links to user.
    """
    def has_object_permission(self, request, view, obj):
        if not hasattr(obj, 'employee') or not obj.employee.manager:
            return False
        return obj.employee.manager.user == request.user
