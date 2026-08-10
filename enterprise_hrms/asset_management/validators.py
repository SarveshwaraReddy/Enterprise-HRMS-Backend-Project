import datetime
from rest_framework.exceptions import ValidationError


def validate_warranty_dates(purchase_date, warranty_expiry_date):
    """
    Ensure warranty expiry date is not before purchase date.
    """
    if purchase_date and warranty_expiry_date:
        if warranty_expiry_date < purchase_date:
            raise ValidationError(
                "Warranty expiry date cannot be before the purchase date."
            )


def validate_asset_available(asset):
    """
    Ensure the asset is in 'available' status before assigning.
    """
    if asset.status != 'available':
        raise ValidationError(
            f"Asset '{asset.asset_code}' is not available for assignment. "
            f"Current status: {asset.get_status_display()}."
        )


def validate_no_active_assignment(asset):
    """
    Ensure there is no active assignment for the asset (one-to-one rule).
    """
    if asset.assignments.filter(status='active').exists():
        raise ValidationError(
            f"Asset '{asset.asset_code}' is already assigned to an employee. "
            "Please return it before reassigning."
        )


def validate_ticket_not_closed(ticket):
    """
    Prevent editing of a ticket that is already closed.
    """
    if ticket.status == 'closed':
        raise ValidationError(
            f"Ticket '{ticket.ticket_number}' is closed and cannot be edited."
        )


def validate_critical_ticket_has_engineer(priority, assigned_engineer):
    """
    Critical priority tickets must have an assigned engineer.
    """
    if priority == 'critical' and not assigned_engineer:
        raise ValidationError(
            "Critical priority tickets require an assigned engineer."
        )


def validate_license_dates(purchase_date, expiry_date):
    """
    Ensure software license expiry date is not before purchase date.
    """
    if purchase_date and expiry_date:
        if expiry_date < purchase_date:
            raise ValidationError(
                "License expiry date cannot be before the purchase date."
            )
