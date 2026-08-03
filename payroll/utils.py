from .calculations import get_month_attendance_summary
from .pdf_generator import generate_payslip_pdf


def calculate_unpaid_leave_days(employee, month, year):
    """Legacy helper function delegating to calculations engine."""
    summary = get_month_attendance_summary(employee, month, year)
    return int(summary['lwp_days'])
