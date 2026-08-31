import uuid

class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Inject request ID
        request.request_id = str(uuid.uuid4())
        
        # Get IP address
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            request.ip_address = x_forwarded_for.split(',')[0]
        else:
            request.ip_address = request.META.get('REMOTE_ADDR')

        # Get User Agent
        request.user_agent = request.META.get('HTTP_USER_AGENT', '')

        response = self.get_response(request)
        return response
