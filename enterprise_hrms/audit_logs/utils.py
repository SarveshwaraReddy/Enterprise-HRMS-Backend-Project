def log_action(*args, **kwargs):
    """
    Utility to record actions into the AuditLog table.
    Accepts arbitrary args and kwargs to flexibly handle different log formats.
    Expected kwargs: user, action, description, request
    """
    from .models import AuditLog
    
    # Extract known kwargs, fallback to positional if needed
    user = kwargs.get('user')
    if not user and len(args) > 0:
        user = args[0]
        
    action = kwargs.get('action')
    if not action and len(args) > 1:
        action = args[1]
        
    description = kwargs.get('description')
    if not description and len(args) > 2:
        description = args[2]
        
    request = kwargs.get('request')
    if not request and len(args) > 3:
        request = args[3]
    
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
    if user and hasattr(user, 'is_authenticated') and user.is_authenticated:
        log_user = user
        
    # Any extra kwargs can be formatted into the description
    extra_data = {k: v for k, v in kwargs.items() if k not in ['user', 'action', 'description', 'request']}
    if extra_data:
        description = f"{description} | Extra Context: {extra_data}"
        
    return AuditLog.objects.create(
        user=log_user,
        action=action,
        description=description,
        ip_address=ip_address
    )
