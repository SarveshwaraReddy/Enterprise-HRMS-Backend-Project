import datetime
from django.utils import timezone
from rest_framework.exceptions import ValidationError, PermissionDenied

from enterprise_hrms.employees.models import Employee
from enterprise_hrms.audit_logs.utils import log_action
from .models import LeaveType, LeaveBalance, LeaveRequest
from .utils import calculate_leave_days
from .validators import validate_leave_dates, validate_leave_balance, validate_overlapping_leave
from .notifications import (
    notify_leave_applied,
    notify_manager_approved,
    notify_hr_approved,
    notify_leave_rejected,
    notify_leave_cancelled
)


def get_or_create_leave_balance(employee: Employee, leave_type: LeaveType, year: int = None) -> LeaveBalance:
    """
    Retrieves or creates the LeaveBalance for an employee, leave_type, and year.
    Initializes allocated_days with the leave_type's annual_quota if newly created.
    """
    if year is None:
        year = datetime.date.today().year

    balance, created = LeaveBalance.objects.get_or_create(
        employee=employee,
        leave_type=leave_type,
        year=year,
        defaults={
            'allocated_days': leave_type.annual_quota,
            'used_days': 0,
            'remaining_days': leave_type.annual_quota
        }
    )
    return balance


def apply_leave(employee: Employee, leave_type: LeaveType, start_date: datetime.date, end_date: datetime.date, reason: str, is_hr_override: bool = False, request=None) -> LeaveRequest:
    """
    Service method to validate and submit a new leave request.
    """
    # 1. Validate dates
    validate_leave_dates(start_date, end_date, is_hr_override=is_hr_override)

    # 2. Calculate leave duration
    total_days = calculate_leave_days(start_date, end_date)
    if total_days <= 0:
        raise ValidationError("Calculated leave days must be at least 1 day.")

    year = start_date.year
    # Ensure balance record exists
    get_or_create_leave_balance(employee, leave_type, year)

    # 3. Validate balance and overlapping requests
    validate_leave_balance(employee, leave_type, total_days, year=year)
    validate_overlapping_leave(employee, start_date, end_date)

    # Determine initial approval status
    initial_status = 'pending_manager'
    # If employee has no department manager or applied by HR/Admin directly, check condition
    if not (employee.department and employee.department.manager and employee.department.manager != employee):
        initial_status = 'pending_hr'

    leave_request = LeaveRequest.objects.create(
        employee=employee,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        total_days=total_days,
        reason=reason,
        status=initial_status
    )

    # Audit log & notification
    log_user = request.user if request and hasattr(request, 'user') else (employee.user if employee.user else None)
    if log_user:
        log_action(
            user=log_user,
            action="Leave Applied",
            description=f"Leave request #{leave_request.id} applied for {employee} ({leave_type.code}, {total_days} days).",
            request=request
        )

    notify_leave_applied(leave_request)
    return leave_request


def approve_leave(leave_request: LeaveRequest, approver_user, comments: str = "", request=None) -> LeaveRequest:
    """
    Service method for Manager approval step: pending_manager -> pending_hr.
    """
    if leave_request.status != 'pending_manager':
        raise ValidationError(f"Cannot perform manager approval on request with status '{leave_request.get_status_display()}'.")

    try:
        approver_employee = approver_user.employee_profile
    except Employee.DoesNotExist:
        approver_employee = None

    leave_request.manager_comments = comments
    leave_request.manager_approved_by = approver_employee
    leave_request.status = 'pending_hr'
    leave_request.save()

    log_action(
        user=approver_user,
        action="Manager Approved Leave",
        description=f"Manager review completed for Leave #{leave_request.id}: Approved.",
        request=request
    )

    notify_manager_approved(leave_request)
    return leave_request


def reject_leave(leave_request: LeaveRequest, reviewer_user, comments: str = "", request=None) -> LeaveRequest:
    """
    Service method for rejecting a leave request.
    """
    if leave_request.status in ['approved', 'rejected', 'cancelled']:
        raise ValidationError(f"Cannot reject a leave request that is already '{leave_request.get_status_display()}'.")

    try:
        reviewer_employee = reviewer_user.employee_profile
    except Employee.DoesNotExist:
        reviewer_employee = None

    reviewer_role = "Manager"
    if leave_request.status == 'pending_hr' or reviewer_user.role in ['admin', 'hr']:
        leave_request.hr_comments = comments
        leave_request.hr_approved_by = reviewer_employee
        reviewer_role = "HR"
    else:
        leave_request.manager_comments = comments
        leave_request.manager_approved_by = reviewer_employee

    leave_request.status = 'rejected'
    leave_request.save()

    log_action(
        user=reviewer_user,
        action="Leave Rejected",
        description=f"Leave #{leave_request.id} was rejected by {reviewer_role}.",
        request=request
    )

    notify_leave_rejected(leave_request, reviewer_role=reviewer_role, comments=comments)
    return leave_request


def final_approve_leave(leave_request: LeaveRequest, hr_user, comments: str = "", request=None) -> LeaveRequest:
    """
    Service method for HR final approval step: pending_hr -> approved.
    Deducts leave balance upon approval.
    """
    if leave_request.status not in ['pending_hr', 'pending_manager']:
        raise ValidationError(f"Cannot perform final approval on request with status '{leave_request.get_status_display()}'.")

    try:
        hr_employee = hr_user.employee_profile
    except Employee.DoesNotExist:
        hr_employee = None

    year = leave_request.start_date.year
    balance = get_or_create_leave_balance(leave_request.employee, leave_request.leave_type, year)

    if balance.remaining_days < leave_request.total_days:
        raise ValidationError(
            f"Cannot approve: Employee has insufficient leave balance ({balance.remaining_days} remaining vs {leave_request.total_days} requested)."
        )

    # Deduct balance
    balance.used_days += leave_request.total_days
    balance.save()

    leave_request.hr_comments = comments
    leave_request.hr_approved_by = hr_employee
    leave_request.status = 'approved'
    leave_request.approved_at = timezone.now()
    leave_request.save()

    log_action(
        user=hr_user,
        action="HR Approved Leave",
        description=f"HR final approval granted for Leave #{leave_request.id} ({leave_request.total_days} days deducted).",
        request=request
    )

    notify_hr_approved(leave_request)
    return leave_request


def cancel_leave(leave_request: LeaveRequest, user, reason: str = "", request=None) -> LeaveRequest:
    """
    Service method to cancel a leave request.
    If the leave was already approved, restores the employee's leave balance.
    """
    if leave_request.status in ['rejected', 'cancelled']:
        raise ValidationError(f"Leave request is already {leave_request.get_status_display()}.")

    # Check if approved previously -> restore balance
    if leave_request.status == 'approved':
        year = leave_request.start_date.year
        balance = get_or_create_leave_balance(leave_request.employee, leave_request.leave_type, year)
        balance.used_days = max(0, balance.used_days - leave_request.total_days)
        balance.save()

    leave_request.status = 'cancelled'
    leave_request.save()

    log_action(
        user=user,
        action="Leave Cancelled",
        description=f"Leave #{leave_request.id} was cancelled. Balance restored if previously approved.",
        request=request
    )

    notify_leave_cancelled(leave_request)
    return leave_request


def update_leave_balance(employee: Employee, leave_type: LeaveType, year: int, allocated_days: int, used_days: int = None) -> LeaveBalance:
    """
    Updates or creates a LeaveBalance entry for an employee.
    """
    balance, _ = LeaveBalance.objects.get_or_create(
        employee=employee,
        leave_type=leave_type,
        year=year,
        defaults={'allocated_days': allocated_days, 'used_days': 0}
    )
    balance.allocated_days = allocated_days
    if used_days is not None:
        balance.used_days = used_days
    balance.save()
    return balance


def employee_leave_summary(employee: Employee, year: int = None) -> dict:
    """
    Returns a comprehensive leave summary for an employee for a given year.
    """
    if year is None:
        year = datetime.date.today().year

    balances = LeaveBalance.objects.filter(employee=employee, year=year).select_related('leave_type')
    leave_types = LeaveType.objects.all()

    summary_list = []
    # Ensure all leave types are included
    existing_types = {b.leave_type_id: b for b in balances}
    for lt in leave_types:
        if lt.id in existing_types:
            b = existing_types[lt.id]
            allocated = b.allocated_days
            used = b.used_days
            remaining = b.remaining_days
        else:
            allocated = lt.annual_quota
            used = 0
            remaining = lt.annual_quota

        summary_list.append({
            "leave_type_id": lt.id,
            "leave_type_name": lt.name,
            "code": lt.code,
            "is_paid": lt.is_paid,
            "allocated_days": allocated,
            "used_days": used,
            "remaining_days": remaining,
            "year": year
        })

    return {
        "employee_id": employee.id,
        "employee_code": employee.employee_id,
        "employee_name": f"{employee.first_name} {employee.last_name}",
        "year": year,
        "balances": summary_list
    }
