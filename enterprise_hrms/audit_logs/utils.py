def log_action(user, action, description, request=None):
    """
    Utility to record actions into the AuditLog table.
    """
    from .models import AuditLog
    
    # Resolve IP address
    ip_address = None
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0].strip()
        else:
            ip_address = request.META.get('REMOTE_ADDR')
            
    # Handle unauthenticated user or anonymous user
    log_user = None
    if user and user.is_authenticated:
        log_user = user
        
    return AuditLog.objects.create(
        user=log_user,
        action=action,
        description=description,
        ip_address=ip_address
    )
