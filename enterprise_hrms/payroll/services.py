from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, Count
from rest_framework.exceptions import ValidationError, NotFound

from .models import SalaryStructure, PayrollRun, Payslip
from .validators import (
    validate_payroll_run_not_released,
    validate_payroll_approval_for_release,
    validate_salary_structure_exists,
    validate_single_payroll_run_per_month,
    validate_non_negative_net_salary
)
from .calculations import (
    calculate_gross_salary,
    calculate_base_deductions,
    calculate_lwp_deduction,
    calculate_full_salary_breakdown,
    get_month_attendance_summary
)
from .pdf_generator import generate_payslip_pdf
from .reports import (
    get_payroll_summary_report,
    get_department_payroll_report,
    get_employee_salary_history
)
from enterprise_hrms.employees.models import Employee
from enterprise_hrms.notifications.utils import create_notification
from enterprise_hrms.audit_logs.utils import log_action


class PayrollService:
    """
    Payroll Service Layer enforcing all business workflow and rules.
    Views communicate strictly through this service layer.
    """

    @staticmethod
    def create_salary_structure(employee_id, data):
        try:
            employee = Employee.objects.get(id=employee_id)
        except Employee.DoesNotExist:
            raise NotFound(f"Employee with ID {employee_id} not found.")

        status = data.get('status', 'active')
        if status == 'active':
            SalaryStructure.objects.filter(employee=employee, status='active').update(status='inactive')

        def to_dec(val):
            return Decimal(str(val)) if val is not None and val != "" else Decimal("0.00")

        salary_structure = SalaryStructure.objects.create(
            employee=employee,
            basic_salary=to_dec(data.get('basic_salary', 0)),
            house_rent_allowance=to_dec(data.get('house_rent_allowance', 0)),
            special_allowance=to_dec(data.get('special_allowance', 0)),
            travel_allowance=to_dec(data.get('travel_allowance', 0)),
            medical_allowance=to_dec(data.get('medical_allowance', 0)),
            provident_fund=to_dec(data.get('provident_fund', 0)),
            professional_tax=to_dec(data.get('professional_tax', 0)),
            income_tax=to_dec(data.get('income_tax', 0)),
            other_deductions=to_dec(data.get('other_deductions', 0)),
            effective_from=data.get('effective_from', timezone.now().date()),
            status=status
        )
        return salary_structure

    @staticmethod
    def update_salary_structure(structure_id, data):
        try:
            structure = SalaryStructure.objects.get(id=structure_id)
        except SalaryStructure.DoesNotExist:
            raise NotFound(f"Salary structure with ID {structure_id} not found.")

        decimal_fields = {
            'basic_salary', 'house_rent_allowance', 'special_allowance',
            'travel_allowance', 'medical_allowance', 'provident_fund',
            'professional_tax', 'income_tax', 'other_deductions'
        }

        for key, value in data.items():
            if hasattr(structure, key):
                if key in decimal_fields:
                    setattr(structure, key, Decimal(str(value)))
                else:
                    setattr(structure, key, value)
        structure.save()
        return structure

    @staticmethod
    def delete_salary_structure(structure_id):
        try:
            structure = SalaryStructure.objects.get(id=structure_id)
        except SalaryStructure.DoesNotExist:
            raise NotFound(f"Salary structure with ID {structure_id} not found.")
        structure.delete()

    @staticmethod
    @transaction.atomic
    def create_payroll_run(payroll_month, payroll_year, processed_by, remarks=None):
        """
        Module 5: create_payroll_run()
        Business Rule: Only one payroll run per month.
        Generates payslips for all active employees with salary structures.
        """
        payroll_month = int(payroll_month)
        payroll_year = int(payroll_year)
        validate_single_payroll_run_per_month(payroll_month, payroll_year)

        payroll_run = PayrollRun.objects.create(
            payroll_month=payroll_month,
            payroll_year=payroll_year,
            status='processing',
            processed_by=processed_by,
            processed_at=timezone.now(),
            remarks=remarks
        )

        active_employees = Employee.objects.filter(status='active')

        for emp in active_employees:
            try:
                validate_salary_structure_exists(emp)
                PayrollService.generate_payslip(emp, payroll_run)
            except ValidationError:
                continue

        payroll_run.status = 'draft'
        payroll_run.save()
        return payroll_run

    @staticmethod
    def calculate_salary(employee, month, year, salary_structure=None):
        if not salary_structure:
            salary_structure = validate_salary_structure_exists(employee)
        breakdown = calculate_full_salary_breakdown(salary_structure, int(month), int(year))
        return breakdown

    @staticmethod
    def calculate_deductions(salary_structure, lwp_days=0, working_days=30):
        gross = calculate_gross_salary(salary_structure)
        base_ded = calculate_base_deductions(salary_structure)
        lwp_ded = calculate_lwp_deduction(gross, lwp_days, working_days)
        return base_ded + lwp_ded

    @staticmethod
    @transaction.atomic
    def generate_payslip(employee, payroll_run):
        validate_payroll_run_not_released(payroll_run)
        salary_structure = validate_salary_structure_exists(employee)

        month = payroll_run.payroll_month
        year = payroll_run.payroll_year

        breakdown = PayrollService.calculate_salary(employee, month, year, salary_structure)
        validate_non_negative_net_salary(breakdown['net_salary'])

        payslip, created = Payslip.objects.update_or_create(
            employee=employee,
            payroll_run=payroll_run,
            defaults={
                'gross_salary': breakdown['gross_salary'],
                'total_deductions': breakdown['total_deductions'],
                'net_salary': breakdown['net_salary'],
                'working_days': breakdown['working_days'],
                'present_days': breakdown['present_days'],
                'leave_days': breakdown['leave_days'],
                'overtime_hours': breakdown['overtime_hours'],
            }
        )

        generate_payslip_pdf(payslip)
        return payslip

    @staticmethod
    @transaction.atomic
    def approve_payroll(payroll_run_id, approved_by):
        try:
            payroll_run = PayrollRun.objects.get(id=payroll_run_id)
        except PayrollRun.DoesNotExist:
            raise NotFound(f"Payroll run with ID {payroll_run_id} not found.")

        validate_payroll_run_not_released(payroll_run)

        payroll_run.status = 'approved'
        payroll_run.approved_by = approved_by
        payroll_run.approved_at = timezone.now()
        payroll_run.save()
        return payroll_run

    @staticmethod
    @transaction.atomic
    def release_payroll(payroll_run_id):
        try:
            payroll_run = PayrollRun.objects.get(id=payroll_run_id)
        except PayrollRun.DoesNotExist:
            raise NotFound(f"Payroll run with ID {payroll_run_id} not found.")

        validate_payroll_approval_for_release(payroll_run)

        payroll_run.status = 'released'
        payroll_run.save()

        for slip in payroll_run.payslips.all():
            if slip.employee.user:
                create_notification(
                    recipient=slip.employee.user,
                    title="Payroll Released",
                    message=f"Your payslip for {payroll_run.payroll_month}/{payroll_run.payroll_year} has been released. Net Salary: ${slip.net_salary:,.2f}"
                )

        return payroll_run

    @staticmethod
    def payroll_summary(payroll_run_id=None, month=None, year=None):
        return get_payroll_summary_report(payroll_run_id=payroll_run_id, month=month, year=year)

    @staticmethod
    def get_dashboard_analytics():
        latest_run = PayrollRun.objects.order_by('-payroll_year', '-payroll_month').first()
        status = latest_run.status if latest_run else 'No Runs'
        employees_processed = Payslip.objects.values('employee').distinct().count()

        pending_payslips = Payslip.objects.filter(payroll_run__status__in=['draft', 'processing']).count()

        total_cost = Payslip.objects.filter(payroll_run__status='released').aggregate(total=Sum('net_salary'))['total'] or Decimal('0.00')

        dept_summary = get_department_payroll_report(
            month=latest_run.payroll_month if latest_run else None,
            year=latest_run.payroll_year if latest_run else None
        )

        return {
            'current_payroll_status': status,
            'latest_payroll_run': {
                'id': latest_run.id if latest_run else None,
                'month': latest_run.payroll_month if latest_run else None,
                'year': latest_run.payroll_year if latest_run else None,
                'status': latest_run.status if latest_run else None
            } if latest_run else None,
            'employees_processed': employees_processed,
            'pending_payslips': pending_payslips,
            'total_payroll_cost': total_cost,
            'department_payroll_summary': dept_summary
        }
