import time
import functools
import logging
from django.core.exceptions import PermissionDenied
from enterprise_hrms.audit_logs.utils import log_action

logger = logging.getLogger(__name__)

def permission_check(allowed_roles):
    """
    Decorator to check if the user has one of the allowed roles.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Assuming first or second argument is request, or kwargs has request
            request = kwargs.get('request_obj') or kwargs.get('request')
            if not request:
                for arg in args:
                    if hasattr(arg, 'user'):
                        request = arg
                        break

            if not request or not hasattr(request, 'user') or not request.user.is_authenticated:
                raise PermissionDenied("Authentication credentials were not provided or invalid.")
                
            if request.user.role not in allowed_roles and not request.user.is_superuser:
                raise PermissionDenied(f"User role '{request.user.role}' is not authorized. Allowed roles: {allowed_roles}")
            return func(*args, **kwargs)
        return wrapper
    return decorator

def audit_action(action_name):
    """
    Decorator to log business actions automatically.
    Expects `request_obj` or `request` in kwargs, or as an argument to extract the user.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            request = kwargs.get('request_obj') or kwargs.get('request')
            if not request:
                for arg in args:
                    if hasattr(arg, 'user'):
                        request = arg
                        break
            
            user = request.user if request and hasattr(request, 'user') else None
            
            try:
                result = func(*args, **kwargs)
                log_action(user=user, action=action_name, description=f"Successfully executed {func.__name__}", request=request)
                return result
            except Exception as e:
                log_action(user=user, action=action_name, description=f"Failed to execute {func.__name__}. Error: {str(e)}", request=request)
                raise
        return wrapper
    return decorator

def execution_timing(func):
    """
    Decorator to measure execution time of a function.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        logger.info(f"Function '{func.__name__}' executed in {execution_time:.4f} seconds.")
        return result
    return wrapper

def business_validation(validator_func):
    """
    Decorator to run a custom validation function before executing the main function.
    If validator_func raises an exception or returns False, it blocks execution.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # The validator must accept the same args and kwargs
            validator_func(*args, **kwargs)
            return func(*args, **kwargs)
        return wrapper
    return decorator
