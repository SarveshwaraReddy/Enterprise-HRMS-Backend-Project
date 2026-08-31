import datetime
from enterprise_hrms.audit_logs.utils import log_action
from .models import AssetMaintenance, Asset
from rest_framework.exceptions import ValidationError


def complete_maintenance(maintenance: AssetMaintenance, completed_date=None,
                         user=None, request=None) -> AssetMaintenance:
    """
    Marks a maintenance record as completed and sets the asset status
    back to 'available'.

    Args:
        maintenance: The AssetMaintenance instance to complete.
        completed_date: Optional date of completion; defaults to today.
        user: The user performing the action (for audit logging).
        request: The HTTP request object (for IP resolution in audit logs).

    Returns:
        The updated AssetMaintenance instance.

    Raises:
        ValidationError: If the maintenance is already completed.
    """
    if maintenance.status == 'completed':
        raise ValidationError(
            f"Maintenance record #{maintenance.id} for asset "
            f"'{maintenance.asset.asset_code}' is already marked as completed."
        )

    if maintenance.status == 'cancelled':
        raise ValidationError(
            f"Maintenance record #{maintenance.id} is cancelled and cannot be completed."
        )

    if completed_date is None:
        completed_date = datetime.date.today()

    maintenance.status = 'completed'
    maintenance.completed_date = completed_date
    maintenance.save(update_fields=['status', 'completed_date', 'updated_at'])

    # Set asset back to available
    asset = maintenance.asset
    asset.status = 'available'
    asset.save(update_fields=['status'])

    log_action(
        user=user,
        action="Maintenance Completed",
        description=(
            f"Maintenance record #{maintenance.id} for asset "
            f"'{asset.asset_code}' completed on {completed_date}."
        ),
        request=request,
    )

    return maintenance


def cancel_maintenance(maintenance: AssetMaintenance, user=None, request=None) -> AssetMaintenance:
    """
    Cancels a scheduled or in-progress maintenance record and sets
    the asset back to 'available'.

    Args:
        maintenance: The AssetMaintenance instance to cancel.
        user: The user performing the action.
        request: The HTTP request object.

    Returns:
        The updated AssetMaintenance instance.

    Raises:
        ValidationError: If the maintenance is already completed or cancelled.
    """
    if maintenance.status in ['completed', 'cancelled']:
        raise ValidationError(
            f"Maintenance record #{maintenance.id} cannot be cancelled "
            f"(current status: {maintenance.get_status_display()})."
        )

    maintenance.status = 'cancelled'
    maintenance.save(update_fields=['status', 'updated_at'])

    # Free the asset back to available
    asset = maintenance.asset
    asset.status = 'available'
    asset.save(update_fields=['status'])

    log_action(
        user=user,
        action="Maintenance Cancelled",
        description=(
            f"Maintenance record #{maintenance.id} for asset "
            f"'{asset.asset_code}' was cancelled."
        ),
        request=request,
    )

    return maintenance
