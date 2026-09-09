from rest_framework.response import Response

def success_response(data=None, message="Success", status_code=200):
    """
    Standard format for successful API responses.
    """
    return Response({
        "success": True,
        "message": message,
        "data": data
    }, status=status_code)

def error_response(errors=None, message="Error", status_code=400, error_code=None):
    """
    Standard format for error API responses.
    """
    response_data = {
        "success": False,
        "message": message,
        "errors": errors
    }
    
    if error_code is not None:
        response_data["error_code"] = error_code
        
    return Response(response_data, status=status_code)
