from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError
from .responses import error_response

def custom_exception_handler(exc, context):
    """
    Custom exception handler to format errors to our standard envelope.
    """
    response = exception_handler(exc, context)
    
    if response is not None:
        # Standardize validation errors
        if isinstance(exc, ValidationError):
            errors = response.data
            # Extract standard message if present, else construct validation message
            message = "Validation failed."
            return error_response(errors=errors, message=message, status_code=response.status_code)
        
        # Standardize other exceptions (e.g. AuthenticationFailed, NotAuthenticated, PermissionDenied)
        errors = response.data
        message = errors.get("detail", "An error occurred.")
        return error_response(errors=errors, message=message, status_code=response.status_code)
        
    return response
