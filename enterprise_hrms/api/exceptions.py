from rest_framework.views import exception_handler
from rest_framework.exceptions import ValidationError
from .responses import error_response

def custom_exception_handler(exc, context):
    """
    Custom exception handler to format errors to our standard enterprise envelope.
    {
        "success": false,
        "message": "Unable to process request",
        "error_code": "...",
        "details": {}
    }
    """
    response = exception_handler(exc, context)
    
    if response is not None:
        errors = response.data
        
        if isinstance(exc, ValidationError):
            return error_response(
                errors=errors, 
                message="Validation failed.", 
                status_code=response.status_code,
                error_code="VALIDATION_FAILED"
            )
            
        message = errors.get("detail", "An error occurred.")
        error_code = getattr(exc, 'default_code', "UNEXPECTED_ERROR").upper()
        
        return error_response(
            errors=errors, 
            message=message, 
            status_code=response.status_code,
            error_code=error_code
        )
        
    return response
