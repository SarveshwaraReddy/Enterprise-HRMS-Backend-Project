from rest_framework import permissions

class IsAdmin(permissions.BasePermission):
    """
    Allows access only to Admin users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (request.user.role == 'admin' or request.user.is_superuser))


class IsHR(permissions.BasePermission):
    """
    Allows access only to HR users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == 'hr')


class IsAdminOrHR(permissions.BasePermission):
    """
    Allows access to Admin or HR users.
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
        return bool(request.user and request.user.is_authenticated and request.user.role == 'employee')


class IsOwnerOrAdminOrHR(permissions.BasePermission):
    """
    Allows access to owners of the resource, department managers, or Admin/HR users.
    """
    def has_object_permission(self, request, view, obj):
        # Admin or HR can access anything
        if request.user.is_superuser or request.user.role in ['admin', 'hr']:
            return True
            
        # Check if the object has a relationship to the request user
        # 1. User instance check
        if hasattr(obj, 'email') and obj == request.user:
            return True
            
        # 2. Employee instance check
        if hasattr(obj, 'user') and obj.user == request.user:
            return True
            
        # 3. Related Employee check (e.g., Attendance, LeaveRequest, Payroll, Document)
        if hasattr(obj, 'employee') and obj.employee and obj.employee.user == request.user:
            return True
            
        # 4. Department Manager check
        try:
            employee_profile = request.user.employee_profile
            if hasattr(obj, 'employee') and obj.employee and obj.employee.department:
                if obj.employee.department.manager == employee_profile:
                    return True
            if hasattr(obj, 'department') and obj.department:
                if obj.department.manager == employee_profile:
                    return True
        except Exception:
            pass
            
        return False
