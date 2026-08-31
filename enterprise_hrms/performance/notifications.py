import logging

logger = logging.getLogger(__name__)

def log_and_notify(event_name, message, recipients=None):
    """
    Mock utility to generate audit logs and notify users.
    In a real system, this could write to an AuditLog model and send emails.
    """
    if recipients is None:
        recipients = []
        
    logger.info(f"AUDIT LOG - Event: {event_name} | Message: {message} | Notified: {recipients}")
    
    # Example placeholder for saving to audit logs if the AuditLog model is available:
    try:
        from enterprise_hrms.audit_logs.utils import create_audit_log
        # create_audit_log(event_name, message) # adjust based on actual util signature
    except ImportError:
        pass
