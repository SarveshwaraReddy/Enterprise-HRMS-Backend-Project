import datetime
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from enterprise_hrms.employees.models import Employee
from .models import LeaveType, LeaveBalance, LeaveRequest


def validate_leave_dates(start_date: datetime.date, end_date: datetime.date, is_hr_override: bool = False):
    """
    Validates leave start and end dates according to business rules.
    - End date must be >= start date.
    - Start date cannot be in the past, unless is_hr_override is True.
    """
    if not start_date or not end_date:
        raise ValidationError("Both start_date and end_date are required.")

    if end_date < start_date:
        raise ValidationError("End date must be greater than or equal to start date.")

    today = datetime.date.today()
    if start_date < today and not is_hr_override:
        raise ValidationError("Leave start date cannot be in the past.")


def validate_overlapping_leave(employee: Employee, start_date: datetime.date, end_date: datetime.date, exclude_request_id: int = None):
    """
    Validates that the employee does not have active overlapping leave requests.
    Active requests are those with status pending_manager, pending_hr, or approved.
    """
    queryset = LeaveRequest.objects.filter(
        employee=employee,
        status__in=['pending_manager', 'pending_hr', 'approved'],
        start_date__lte=end_date,
        end_date__gte=start_date
    )

    if exclude_request_id:
        queryset = queryset.exclude(id=exclude_request_id)

    if queryset.exists():
        overlapping = queryset.first()
        raise ValidationError(
            f"Overlapping leave request found from {overlapping.start_date} to {overlapping.end_date} (Status: {overlapping.get_status_display()})."
        )


def validate_leave_balance(employee: Employee, leave_type: LeaveType, total_days: int, year: int = None):
    """
    Validates that the employee has sufficient remaining leave balance for the requested leave type.
    """
    if year is None:
        year = datetime.date.today().year

    try:
        balance = LeaveBalance.objects.get(employee=employee, leave_type=leave_type, year=year)
    except LeaveBalance.DoesNotExist:
        # If no balance record exists, check leave type annual quota or raise error
        if leave_type.annual_quota < total_days:
            raise ValidationError(
                f"Insufficient leave balance for {leave_type.name}. Requested: {total_days} day(s), Allocated: {leave_type.annual_quota} day(s)."
            )
        return

    if balance.remaining_days < total_days:
        raise ValidationError(
            f"Insufficient leave balance for {leave_type.name}. Requested: {total_days} day(s), Remaining balance: {balance.remaining_days} day(s)."
        )
