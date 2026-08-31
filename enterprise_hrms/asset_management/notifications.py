from enterprise_hrms.notifications.utils import create_notification
from enterprise_hrms.accounts.models import User


def notify_asset_assigned(assignment):
    """
    Sends notification to the employee when an asset is assigned to them.
    """
    employee = assignment.employee
    if employee and employee.user:
        create_notification(
            recipient=employee.user,
            title="Asset Assigned to You",
            message=(
                f"Asset '{assignment.asset.asset_code}' ({assignment.asset.name}) "
                f"has been assigned to you on {assignment.assigned_date}. "
                f"Expected return: {assignment.expected_return_date or 'Not specified'}."
            )
        )

    # Notify IT admins
    it_users = User.objects.filter(role__in=['admin', 'it'])
    for it_user in it_users:
        create_notification(
            recipient=it_user,
            title="Asset Assignment Confirmation",
            message=(
                f"Asset '{assignment.asset.asset_code}' has been assigned to "
                f"{employee.first_name} {employee.last_name}."
            )
        )


def notify_asset_return_reminder(assignment):
    """
    Sends a reminder to the employee when the asset return date is approaching.
    """
    employee = assignment.employee
    if employee and employee.user:
        create_notification(
            recipient=employee.user,
            title="Asset Return Reminder",
            message=(
                f"Please note that asset '{assignment.asset.asset_code}' "
                f"({assignment.asset.name}) is due for return on "
                f"{assignment.expected_return_date}."
            )
        )


def notify_ticket_assigned(ticket):
    """
    Notifies the assigned engineer and the ticket creator when an engineer is assigned.
    """
    engineer = ticket.assigned_engineer
    if engineer and engineer.user:
        create_notification(
            recipient=engineer.user,
            title="Support Ticket Assigned to You",
            message=(
                f"Ticket '{ticket.ticket_number}' [{ticket.get_priority_display()} priority] "
                f"has been assigned to you. Subject: {ticket.subject}."
            )
        )

    employee = ticket.employee
    if employee and employee.user:
        create_notification(
            recipient=employee.user,
            title="Ticket Assignment Update",
            message=(
                f"Your support ticket '{ticket.ticket_number}' has been assigned to "
                f"{engineer.first_name} {engineer.last_name} and is now In Progress."
                if engineer else
                f"Your support ticket '{ticket.ticket_number}' has been updated."
            )
        )


def notify_ticket_resolved(ticket):
    """
    Notifies the ticket creator when their ticket is resolved/closed.
    """
    employee = ticket.employee
    if employee and employee.user:
        create_notification(
            recipient=employee.user,
            title="Support Ticket Resolved",
            message=(
                f"Your support ticket '{ticket.ticket_number}' has been resolved and closed. "
                f"Resolution: {ticket.resolution_notes or 'No notes provided.'}"
            )
        )


def notify_warranty_expiry(asset):
    """
    Alerts IT admins when an asset's warranty is approaching expiry.
    """
    it_users = User.objects.filter(role__in=['admin', 'it'])
    for it_user in it_users:
        create_notification(
            recipient=it_user,
            title="Warranty Expiry Alert",
            message=(
                f"Asset '{asset.asset_code}' ({asset.name}) warranty expires on "
                f"{asset.warranty_expiry_date}. Please take action."
            )
        )


def notify_license_expiry(license):
    """
    Alerts IT admins when a software license is approaching expiry.
    """
    it_users = User.objects.filter(role__in=['admin', 'it'])
    for it_user in it_users:
        create_notification(
            recipient=it_user,
            title="Software License Expiry Alert",
            message=(
                f"Software license for '{license.software_name}' expires on "
                f"{license.expiry_date}. Please renew."
            )
        )

    # Also notify the assigned employee if any
    if license.assigned_employee and license.assigned_employee.user:
        create_notification(
            recipient=license.assigned_employee.user,
            title="Your Software License is Expiring",
            message=(
                f"Your license for '{license.software_name}' expires on {license.expiry_date}. "
                "Please contact IT for renewal."
            )
        )
