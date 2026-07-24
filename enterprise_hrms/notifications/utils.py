def create_notification(recipient, title, message):
    """
    Utility to create a notification for a user.
    """
    from .models import Notification
    return Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message
    )
