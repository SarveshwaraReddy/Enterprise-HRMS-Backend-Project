from rest_framework.views import APIView
from rest_framework import permissions
from django.http import HttpResponse
import datetime
from enterprise_hrms.employees.models import Employee
from enterprise_hrms.departments.models import Department
from enterprise_hrms.attendance.models import Attendance
from enterprise_hrms.payroll.models import Payroll
from enterprise_hrms.api.permissions import IsAdminOrHR
from .utils import generate_csv_report, generate_excel_report, generate_pdf_report


def get_report_response(format_type, title, headers, rows):
    """
    Helper to bundle data, generate report format, and return HTTP response.
    """
    format_type = format_type.lower() if format_type else "csv"

    if format_type == "excel":
        content = generate_excel_report(title, headers, rows)
        content_type = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        filename = f"{title.replace(' ', '_').lower()}_{datetime.date.today()}.xlsx"
    elif format_type == "pdf":
        content = generate_pdf_report(title, headers, rows)
        content_type = "application/pdf"
        filename = f"{title.replace(' ', '_').lower()}_{datetime.date.today()}.pdf"
    else:  # Default CSV
        content = generate_csv_report(headers, rows)
        content_type = "text/csv"
        filename = f"{title.replace(' ', '_').lower()}_{datetime.date.today()}.csv"

    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


class EmployeeReportView(APIView):
    """
    Generate Employee Report.
    Filters: department_id, status.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdminOrHR]

    def get(self, request):
        dept_id = request.query_params.get("department_id")
        emp_status = request.query_params.get("status")
        format_type = request.query_params.get("report_format", "csv")

        queryset = Employee.objects.all().select_related("department")
        if dept_id:
            queryset = queryset.filter(department_id=dept_id)
        if emp_status:
            queryset = queryset.filter(status=emp_status)

        headers = [
            "Employee ID",
            "First Name",
            "Last Name",
            "Email",
            "Phone",
            "DOB",
            "Gender",
            "Department",
            "Designation",
            "Salary",
            "Joining Date",
            "Status",
        ]

        rows = []
        for emp in queryset:
            rows.append(
                [
                    emp.employee_id,
                    emp.first_name,
                    emp.last_name,
                    emp.email,
                    emp.phone or "",
                    emp.dob.strftime("%Y-%m-%d") if emp.dob else "",
                    emp.get_gender_display(),
                    emp.department.name if emp.department else "N/A",
                    emp.designation,
                    emp.salary,
                    emp.joining_date.strftime("%Y-%m-%d") if emp.joining_date else "",
                    emp.get_status_display(),
                ]
            )

        return get_report_response(format_type, "Employee Report", headers, rows)


class DepartmentReportView(APIView):
    """
    Generate Department Report.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdminOrHR]

    def get(self, request):
        format_type = request.query_params.get("report_format", "csv")
        queryset = Department.objects.all().select_related("manager")

        headers = [
            "Department Name",
            "Code",
            "Manager",
            "Description",
            "Employee Count",
        ]

        rows = []
        for dept in queryset:
            manager_name = (
                f"{dept.manager.first_name} {dept.manager.last_name}"
                if dept.manager
                else "N/A"
            )
            rows.append(
                [
                    dept.name,
                    dept.code,
                    manager_name,
                    dept.description,
                    dept.employees.count(),
                ]
            )

        return get_report_response(format_type, "Department Report", headers, rows)


class AttendanceReportView(APIView):
    """
    Generate Attendance Report.
    Filters: start_date, end_date, employee_id.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdminOrHR]

    def get(self, request):
        start_date = request.query_params.get("start_date")
        end_date = request.query_params.get("end_date")
        emp_id = request.query_params.get("employee_id")
        format_type = request.query_params.get("report_format", "csv")

        queryset = Attendance.objects.all().select_related("employee")

        if start_date:
            queryset = queryset.filter(date__gte=start_date)
        if end_date:
            queryset = queryset.filter(date__lte=end_date)
        if emp_id:
            queryset = queryset.filter(employee_id=emp_id)

        headers = [
            "Employee ID",
            "Employee Name",
            "Date",
            "Check-In",
            "Check-Out",
            "Status",
        ]

        rows = []
        for att in queryset:
            check_in_str = att.check_in.strftime("%H:%M:%S") if att.check_in else "N/A"
            check_out_str = (
                att.check_out.strftime("%H:%M:%S") if att.check_out else "N/A"
            )
            rows.append(
                [
                    att.employee.employee_id,
                    f"{att.employee.first_name} {att.employee.last_name}",
                    att.date.strftime("%Y-%m-%d") if att.date else "",
                    check_in_str,
                    check_out_str,
                    att.get_status_display(),
                ]
            )

        return get_report_response(format_type, "Attendance Report", headers, rows)


class PayrollReportView(APIView):
    """
    Generate Payroll Report.
    Filters: month, year.
    """

    permission_classes = [permissions.IsAuthenticated, IsAdminOrHR]

    def get(self, request):
        month = request.query_params.get("month")
        year = request.query_params.get("year")
        format_type = request.query_params.get("report_format", "csv")

        queryset = Payroll.objects.all().select_related("employee")

        if month:
            queryset = queryset.filter(month=month)
        if year:
            queryset = queryset.filter(year=year)

        headers = [
            "Employee ID",
            "Employee Name",
            "Month",
            "Year",
            "Basic Salary",
            "Allowances",
            "Deductions",
            "Net Salary",
            "Status",
        ]

        rows = []
        for pay in queryset:
            rows.append(
                [
                    pay.employee.employee_id,
                    f"{pay.employee.first_name} {pay.employee.last_name}",
                    pay.month,
                    pay.year,
                    pay.basic_salary,
                    pay.allowances,
                    pay.deductions,
                    pay.net_salary,
                    pay.get_status_display(),
                ]
            )

        return get_report_response(format_type, "Payroll Report", headers, rows)
