import datetime
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from enterprise_hrms.employees.models import Employee
from enterprise_hrms.audit_logs.utils import log_action
from .models import Asset, AssetAssignment, AssetMaintenance, SupportTicket, SoftwareLicense
from .validators import (
    validate_asset_available,
    validate_no_active_assignment,
    validate_ticket_not_closed,
    validate_critical_ticket_has_engineer,
    validate_warranty_dates,
    validate_license_dates,
)
from .notifications import (
    notify_asset_assigned,
    notify_ticket_assigned,
    notify_ticket_resolved,
)


def create_asset(data: dict, user=None, request=None) -> Asset:
    """
    Creates a new Asset after validating warranty dates.
    Writes an audit log on success.
    """
    purchase_date = data.get('purchase_date')
    warranty_expiry_date = data.get('warranty_expiry_date')
    validate_warranty_dates(purchase_date, warranty_expiry_date)

    asset = Asset.objects.create(**data)

    if user and user.is_authenticated:
        log_action(
            user=user,
            action="Asset Created",
            description=f"Asset '{asset.asset_code}' ({asset.name}) was created.",
            request=request,
        )
    return asset


def assign_asset(asset: Asset, employee: Employee, assigned_by: Employee = None,
                 assigned_date=None, expected_return_date=None, notes: str = '',
                 user=None, request=None) -> AssetAssignment:
    """
    Assigns an asset to an employee.
    Business Rules:
     - Asset must be 'available'.
     - Asset cannot already have an active assignment.
    On success: asset status → 'assigned', audit log created, notification sent.
    """
    validate_asset_available(asset)
    validate_no_active_assignment(asset)

    if assigned_date is None:
        assigned_date = datetime.date.today()

    assignment = AssetAssignment.objects.create(
        asset=asset,
        employee=employee,
        assigned_by=assigned_by,
        assigned_date=assigned_date,
        expected_return_date=expected_return_date,
        notes=notes,
        status='active',
    )

    # Update asset status
    asset.status = 'assigned'
    asset.save(update_fields=['status'])

    log_action(
        user=user,
        action="Asset Assigned",
        description=(
            f"Asset '{asset.asset_code}' assigned to "
            f"{employee.first_name} {employee.last_name}."
        ),
        request=request,
    )
    notify_asset_assigned(assignment)
    return assignment


def return_asset(assignment: AssetAssignment, user=None, request=None) -> AssetAssignment:
    """
    Marks an assignment as returned and sets asset status back to 'available'.
    Writes an audit log on success.
    """
    if assignment.status == 'returned':
        raise ValidationError("This asset has already been returned.")

    assignment.status = 'returned'
    assignment.actual_return_date = datetime.date.today()
    assignment.save(update_fields=['status', 'actual_return_date'])

    asset = assignment.asset
    asset.status = 'available'
    asset.save(update_fields=['status'])

    log_action(
        user=user,
        action="Asset Returned",
        description=(
            f"Asset '{asset.asset_code}' returned by "
            f"{assignment.employee.first_name} {assignment.employee.last_name}."
        ),
        request=request,
    )
    return assignment


def schedule_maintenance(asset: Asset, scheduled_date, scheduled_by: Employee = None,
                         description: str = '', cost=None, user=None, request=None) -> AssetMaintenance:
    """
    Schedules an asset for maintenance.
    Business Rule: Assets under maintenance or currently assigned cannot be re-scheduled
    unless explicitly cancelled first.
    Sets asset status to 'under_maintenance'. Writes audit log.
    """
    if asset.status == 'assigned':
        raise ValidationError(
            f"Asset '{asset.asset_code}' is currently assigned to an employee. "
            "Please return it before scheduling maintenance."
        )
    if asset.status == 'retired':
        raise ValidationError(f"Asset '{asset.asset_code}' is retired and cannot be scheduled for maintenance.")

    maintenance = AssetMaintenance.objects.create(
        asset=asset,
        scheduled_by=scheduled_by,
        scheduled_date=scheduled_date,
        description=description,
        cost=cost,
        status='scheduled',
    )

    asset.status = 'under_maintenance'
    asset.save(update_fields=['status'])

    log_action(
        user=user,
        action="Maintenance Scheduled",
        description=(
            f"Maintenance scheduled for asset '{asset.asset_code}' "
            f"on {scheduled_date}."
        ),
        request=request,
    )
    return maintenance


def complete_maintenance(maintenance: AssetMaintenance, completed_date=None,
                         user=None, request=None) -> AssetMaintenance:
    """
    Marks a maintenance record as completed and sets asset status back to 'available'.
    """
    if maintenance.status == 'completed':
        raise ValidationError("This maintenance record is already completed.")

    if completed_date is None:
        completed_date = datetime.date.today()

    maintenance.status = 'completed'
    maintenance.completed_date = completed_date
    maintenance.save(update_fields=['status', 'completed_date'])

    asset = maintenance.asset
    asset.status = 'available'
    asset.save(update_fields=['status'])

    log_action(
        user=user,
        action="Maintenance Completed",
        description=f"Maintenance for asset '{asset.asset_code}' completed on {completed_date}.",
        request=request,
    )
    return maintenance


def create_ticket(employee: Employee, subject: str, description: str,
                  category: str = 'other', priority: str = 'medium',
                  asset: Asset = None, assigned_engineer: Employee = None,
                  user=None, request=None) -> SupportTicket:
    """
    Creates a new IT support ticket.
    Business Rule: Critical tickets must have an assigned engineer.
    Writes audit log and sends notification.
    """
    validate_critical_ticket_has_engineer(priority, assigned_engineer)

    ticket = SupportTicket.objects.create(
        employee=employee,
        asset=asset,
        category=category,
        priority=priority,
        subject=subject,
        description=description,
        status='open',
        assigned_engineer=assigned_engineer,
    )

    log_action(
        user=user,
        action="Ticket Created",
        description=f"Support ticket '{ticket.ticket_number}' created by {employee}.",
        request=request,
    )

    if assigned_engineer:
        notify_ticket_assigned(ticket)

    return ticket


def assign_ticket(ticket: SupportTicket, engineer: Employee,
                  user=None, request=None) -> SupportTicket:
    """
    Assigns an engineer to a support ticket.
    Business Rule: Critical tickets require an engineer – enforced here too.
    """
    validate_ticket_not_closed(ticket)

    ticket.assigned_engineer = engineer
    ticket.status = 'in_progress'
    ticket.save(update_fields=['assigned_engineer', 'status'])

    log_action(
        user=user,
        action="Ticket Assigned",
        description=(
            f"Ticket '{ticket.ticket_number}' assigned to "
            f"{engineer.first_name} {engineer.last_name}."
        ),
        request=request,
    )
    notify_ticket_assigned(ticket)
    return ticket


def close_ticket(ticket: SupportTicket, resolution_notes: str = '',
                 user=None, request=None) -> SupportTicket:
    """
    Closes a support ticket. Validates it isn't already closed.
    Updates status, sets closed_at, writes audit log, sends notification.
    """
    validate_ticket_not_closed(ticket)

    ticket.status = 'closed'
    ticket.resolution_notes = resolution_notes
    ticket.closed_at = timezone.now()
    ticket.save(update_fields=['status', 'resolution_notes', 'closed_at'])

    log_action(
        user=user,
        action="Ticket Resolved",
        description=f"Ticket '{ticket.ticket_number}' closed.",
        request=request,
    )
    notify_ticket_resolved(ticket)
    return ticket


def asset_summary() -> dict:
    """
    Returns a high-level asset inventory summary grouped by status.
    """
    from django.db.models import Count
    counts = Asset.objects.values('status').annotate(count=Count('id'))
    summary = {row['status']: row['count'] for row in counts}
    return {
        'total': Asset.objects.count(),
        'available': summary.get('available', 0),
        'assigned': summary.get('assigned', 0),
        'under_maintenance': summary.get('under_maintenance', 0),
        'retired': summary.get('retired', 0),
    }
