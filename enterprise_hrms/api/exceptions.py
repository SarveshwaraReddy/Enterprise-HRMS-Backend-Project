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

class HRMSBaseException(Exception):
    """Base exception for all custom HRMS exceptions."""
    def __init__(self, message, error_code="HRMS_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

class EmployeeNotFoundError(HRMSBaseException):
    def __init__(self, employee_id):
        super().__init__(f"Employee with ID {employee_id} not found.", "EMPLOYEE_NOT_FOUND")

class PayrollAlreadyProcessedError(HRMSBaseException):
    def __init__(self, month, year):
        super().__init__(f"Payroll already processed for {month}/{year}.", "PAYROLL_ALREADY_PROCESSED")

class InsufficientLeaveBalanceError(HRMSBaseException):
    def __init__(self, leave_type):
        super().__init__(f"Insufficient leave balance for {leave_type}.", "INSUFFICIENT_LEAVE_BALANCE")

class AssetAlreadyAssignedError(HRMSBaseException):
    def __init__(self, asset_id):
        super().__init__(f"Asset {asset_id} is already assigned to another employee.", "ASSET_ALREADY_ASSIGNED")

class InvalidWorkflowStateError(HRMSBaseException):
    def __init__(self, current_state, expected_state):
        super().__init__(f"Invalid state: {current_state}. Expected: {expected_state}.", "INVALID_WORKFLOW_STATE")
