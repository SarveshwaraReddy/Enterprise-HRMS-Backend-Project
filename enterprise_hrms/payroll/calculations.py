import calendar
from decimal import Decimal
from django.utils import timezone
from enterprise_hrms.attendance.models import Attendance
from enterprise_hrms.leave_management.models import LeaveRequest


def calculate_gross_salary(salary_structure):
    """
    Gross Salary = Basic Salary + HRA + Special Allowance + Medical Allowance + Travel Allowance
    """
    return (
        salary_structure.basic_salary +
        salary_structure.house_rent_allowance +
        salary_structure.special_allowance +
        salary_structure.medical_allowance +
        salary_structure.travel_allowance
    )


def calculate_base_deductions(salary_structure):
    """
    Base Deductions = PF + Professional Tax + Income Tax + Other Deductions
    """
    return (
        salary_structure.provident_fund +
        salary_structure.professional_tax +
        salary_structure.income_tax +
        salary_structure.other_deductions
    )


def calculate_lwp_deduction(gross_salary, lwp_days, working_days=30):
    """
    Calculate Leave Without Pay (LWP) deduction pro-rated by working days.
    """
    if working_days <= 0 or lwp_days <= 0:
        return Decimal('0.00')
    daily_rate = gross_salary / Decimal(str(working_days))
    deduction = daily_rate * Decimal(str(lwp_days))
    return round(deduction, 2)


def calculate_overtime_pay(gross_salary, overtime_hours, working_days=30):
    """
    Calculate Overtime Pay based on 1.5x hourly rate.
    Hourly Rate = Gross Salary / (working_days * 8)
    """
    if working_days <= 0 or overtime_hours <= 0:
        return Decimal('0.00')
    hourly_rate = gross_salary / (Decimal(str(working_days)) * Decimal('8.0'))
    overtime_pay = hourly_rate * Decimal('1.5') * Decimal(str(overtime_hours))
    return round(overtime_pay, 2)


def calculate_net_salary(gross_salary, total_deductions, overtime_pay=Decimal('0.00')):
    """
    Net Salary = Gross Salary + Overtime Pay - Total Deductions
    Net salary cannot be negative.
    """
    net = gross_salary + overtime_pay - total_deductions
    return max(Decimal('0.00'), round(net, 2))


def get_month_attendance_summary(employee, month, year):
    """
    Calculates working_days, present_days, leave_days, lwp_days, overtime_hours
    from Attendance and LeaveRequest models for the given employee, month, and year.
    """
    _, days_in_month = calendar.monthrange(year, month)
    working_days = days_in_month

    # Filter attendance records for month & year
    attendances = Attendance.objects.filter(
        employee=employee,
        date__year=year,
        date__month=month
    )

    present_count = attendances.filter(status__in=['present', 'late']).count()
    half_day_count = attendances.filter(status='half_day').count()
    absent_count = attendances.filter(status='absent').count()

    present_days = Decimal(str(present_count)) + (Decimal(str(half_day_count)) * Decimal('0.5'))

    # Approved leave requests intersecting month/year
    approved_leaves = LeaveRequest.objects.filter(
        employee=employee,
        status='approved',
        start_date__lte=f"{year:04d}-{month:02d}-{days_in_month:02d}",
        end_date__gte=f"{year:04d}-{month:02d}-01"
    )

    total_leave_days = Decimal('0.0')
    lwp_days = Decimal('0.0')

    for leave in approved_leaves:
        # Calculate overlap days within this month
        month_start = timezone.datetime(year, month, 1).date()
        month_end = timezone.datetime(year, month, days_in_month).date()
        overlap_start = max(leave.start_date, month_start)
        overlap_end = min(leave.end_date, month_end)
        if overlap_start <= overlap_end:
            overlap_days = (overlap_end - overlap_start).days + 1
            total_leave_days += Decimal(str(overlap_days))
            if hasattr(leave, 'leave_type') and leave.leave_type and not leave.leave_type.is_paid:
                lwp_days += Decimal(str(overlap_days))

    # Add unapproved absent days as LWP if attendance records exist
    if absent_count > 0:
        lwp_days += Decimal(str(absent_count))

    overtime_hours = Decimal('0.00')

    return {
        'working_days': working_days,
        'present_days': present_days,
        'leave_days': total_leave_days,
        'lwp_days': lwp_days,
        'overtime_hours': overtime_hours
    }


def calculate_full_salary_breakdown(salary_structure, month, year, attendance_summary=None):
    """
    Computes full payroll breakdown dictionary for an employee.
    """
    employee = salary_structure.employee
    if attendance_summary is None:
        attendance_summary = get_month_attendance_summary(employee, month, year)

    working_days = attendance_summary['working_days']
    present_days = attendance_summary['present_days']
    leave_days = attendance_summary['leave_days']
    lwp_days = attendance_summary['lwp_days']
    overtime_hours = attendance_summary['overtime_hours']

    gross_salary = calculate_gross_salary(salary_structure)
    base_deductions = calculate_base_deductions(salary_structure)
    lwp_deduction = calculate_lwp_deduction(gross_salary, lwp_days, working_days)
    overtime_pay = calculate_overtime_pay(gross_salary, overtime_hours, working_days)

    total_deductions = base_deductions + lwp_deduction
    net_salary = calculate_net_salary(gross_salary, total_deductions, overtime_pay)

    return {
        'employee': employee,
        'gross_salary': gross_salary,
        'base_deductions': base_deductions,
        'lwp_deduction': lwp_deduction,
        'total_deductions': total_deductions,
        'overtime_pay': overtime_pay,
        'net_salary': net_salary,
        'working_days': working_days,
        'present_days': present_days,
        'leave_days': leave_days,
        'lwp_days': lwp_days,
        'overtime_hours': overtime_hours,
        'basic_salary': salary_structure.basic_salary,
        'house_rent_allowance': salary_structure.house_rent_allowance,
        'special_allowance': salary_structure.special_allowance,
        'travel_allowance': salary_structure.travel_allowance,
        'medical_allowance': salary_structure.medical_allowance,
        'provident_fund': salary_structure.provident_fund,
        'professional_tax': salary_structure.professional_tax,
        'income_tax': salary_structure.income_tax,
        'other_deductions': salary_structure.other_deductions,
    }
