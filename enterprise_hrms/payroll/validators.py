from rest_framework.exceptions import ValidationError
from .models import SalaryStructure, PayrollRun


def validate_payroll_run_not_released(payroll_run):
    """
    Business Rule: Released payroll cannot be modified.
    """
    if payroll_run and payroll_run.status == 'released':
        raise ValidationError("Released payroll cannot be modified or reprocessed.")


def validate_payroll_approval_for_release(payroll_run):
    """
    Business Rule: Payroll cannot be released before approval.
    """
    if not payroll_run:
        raise ValidationError("Payroll run does not exist.")
    if payroll_run.status != 'approved':
        raise ValidationError("Payroll cannot be released before it is approved.")


def validate_salary_structure_exists(employee):
    """
    Business Rule: Salary structure must exist before payroll generation.
    """
    structure = SalaryStructure.objects.filter(employee=employee, status='active').first()
    if not structure:
        structure = SalaryStructure.objects.filter(employee=employee).order_by('-effective_from').first()
    if not structure:
        raise ValidationError(f"Salary structure must exist for employee '{employee}' before payroll generation.")
    return structure


def validate_single_payroll_run_per_month(payroll_month, payroll_year, exclude_id=None):
    """
    Business Rule: Only one payroll run per month.
    """
    month = int(payroll_month)
    year = int(payroll_year)
    qs = PayrollRun.objects.filter(payroll_month=month, payroll_year=year)
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    if qs.exists():
        raise ValidationError(f"A payroll run for {month}/{year} already exists.")


def validate_non_negative_net_salary(net_salary):
    """
    Business Rule: Net salary cannot be negative.
    """
    if net_salary < 0:
        raise ValidationError("Net salary cannot be negative.")
