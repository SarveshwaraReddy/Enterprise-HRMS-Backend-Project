from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError, NotFound

from enterprise_hrms.employees.models import Employee
from enterprise_hrms.departments.models import Department
from enterprise_hrms.payroll.models import SalaryStructure, PayrollRun, Payslip
from enterprise_hrms.payroll.services import PayrollService
from enterprise_hrms.payroll.validators import (
    validate_payroll_run_not_released,
    validate_payroll_approval_for_release,
    validate_salary_structure_exists,
    validate_single_payroll_run_per_month,
    validate_non_negative_net_salary
)
from enterprise_hrms.payroll.calculations import (
    calculate_overtime_pay,
    calculate_full_salary_breakdown,
    get_month_attendance_summary
)
from enterprise_hrms.payroll.reports import (
    get_payroll_summary_report,
    get_department_payroll_report,
    get_employee_salary_history,
    export_payroll_report_pdf,
    export_payroll_register_excel,
    export_payroll_transactions_csv
)
from enterprise_hrms.attendance.models import Attendance
from enterprise_hrms.leave_management.models import LeaveType, LeaveRequest

User = get_user_model()


class PayrollServicesTest(TestCase):
    def setUp(self):
        self.hr_user = User.objects.create_user(
            username="hruser",
            email="hr@example.com",
            password="password123",
            role="hr"
        )
        self.dept = Department.objects.create(name="HR", code="HRD")
        self.employee = Employee.objects.create(
            employee_id="EMP101",
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com",
            dob="1992-05-10",
            gender="female",
            department=self.dept,
            designation="HR Specialist",
            salary=Decimal("6000.00"),
            joining_date="2022-01-01",
            status="active"
        )

        self.structure = PayrollService.create_salary_structure(
            employee_id=self.employee.id,
            data={
                "basic_salary": Decimal("4000.00"),
                "house_rent_allowance": Decimal("1000.00"),
                "special_allowance": Decimal("500.00"),
                "travel_allowance": Decimal("300.00"),
                "medical_allowance": Decimal("200.00"),
                "provident_fund": Decimal("400.00"),
                "professional_tax": Decimal("200.00"),
                "income_tax": Decimal("300.00"),
                "other_deductions": Decimal("100.00"),
                "effective_from": timezone.now().date(),
                "status": "active"
            }
        )

    def test_salary_structure_crud_service(self):
        updated = PayrollService.update_salary_structure(
            self.structure.id,
            {"basic_salary": Decimal("4500.00")}
        )
        self.assertEqual(updated.basic_salary, Decimal("4500.00"))

        with self.assertRaises(NotFound):
            PayrollService.update_salary_structure(9999, {"basic_salary": Decimal("1000.00")})

        PayrollService.delete_salary_structure(self.structure.id)
        self.assertFalse(SalaryStructure.objects.filter(id=self.structure.id).exists())

        with self.assertRaises(NotFound):
            PayrollService.delete_salary_structure(self.structure.id)

    def test_calculate_salary_and_deductions(self):
        breakdown = PayrollService.calculate_salary(self.employee, month=8, year=2026)
        self.assertEqual(breakdown['gross_salary'], Decimal("6000.00"))
        self.assertEqual(breakdown['base_deductions'], Decimal("1000.00"))
        self.assertEqual(breakdown['net_salary'], Decimal("5000.00"))

        deductions = PayrollService.calculate_deductions(self.structure, lwp_days=2, working_days=30)
        self.assertEqual(deductions, Decimal("1400.00"))

        overtime = calculate_overtime_pay(Decimal("6000.00"), overtime_hours=10, working_days=30)
        self.assertGreater(overtime, Decimal("0.00"))

    def test_payroll_workflow_create_approve_release(self):
        run = PayrollService.create_payroll_run(
            payroll_month=8,
            payroll_year=2026,
            processed_by=self.hr_user,
            remarks="August Payroll"
        )
        self.assertEqual(run.status, 'draft')
        self.assertTrue(Payslip.objects.filter(payroll_run=run, employee=self.employee).exists())

        with self.assertRaises(ValidationError):
            PayrollService.create_payroll_run(payroll_month=8, payroll_year=2026, processed_by=self.hr_user)

        with self.assertRaises(ValidationError):
            PayrollService.release_payroll(run.id)

        approved_run = PayrollService.approve_payroll(run.id, approved_by=self.hr_user)
        self.assertEqual(approved_run.status, 'approved')
        self.assertEqual(approved_run.approved_by, self.hr_user)

        released_run = PayrollService.release_payroll(run.id)
        self.assertEqual(released_run.status, 'released')
        run.refresh_from_db()

        with self.assertRaises(ValidationError):
            PayrollService.approve_payroll(run.id, approved_by=self.hr_user)

        with self.assertRaises(ValidationError):
            PayrollService.generate_payslip(self.employee, run)

    def test_validators_direct(self):
        with self.assertRaises(ValidationError):
            validate_payroll_approval_for_release(None)

        unapproved_run = PayrollRun.objects.create(payroll_month=1, payroll_year=2030, status='draft')
        with self.assertRaises(ValidationError):
            validate_payroll_approval_for_release(unapproved_run)

        with self.assertRaises(ValidationError):
            validate_non_negative_net_salary(Decimal("-10.00"))

        emp_no_struct = Employee.objects.create(
            employee_id="EMP999",
            first_name="No",
            last_name="Struct",
            email="nostruct@example.com",
            dob="1990-01-01",
            gender="male",
            designation="Tester",
            salary=Decimal("3000.00"),
            joining_date="2023-01-01"
        )
        with self.assertRaises(ValidationError):
            validate_salary_structure_exists(emp_no_struct)

    def test_reports_generation_and_export(self):
        run = PayrollService.create_payroll_run(payroll_month=9, payroll_year=2026, processed_by=self.hr_user)
        summary = get_payroll_summary_report(month=9, year=2026)
        self.assertEqual(summary['total_employees_paid'], 1)

        dept_report = get_department_payroll_report(month=9, year=2026)
        self.assertTrue(len(dept_report) >= 1)

        history = get_employee_salary_history(self.employee.id)
        self.assertTrue(len(history) >= 1)

        pdf_bytes = export_payroll_report_pdf(9, 2026)
        self.assertTrue(len(pdf_bytes) > 0)

        excel_bytes = export_payroll_register_excel(9, 2026)
        self.assertTrue(len(excel_bytes) > 0)

        csv_bytes = export_payroll_transactions_csv(9, 2026)
        self.assertTrue(len(csv_bytes) > 0)

    def test_attendance_and_leave_integration(self):
        Attendance.objects.create(
            employee=self.employee,
            date=timezone.datetime(2026, 8, 5).date(),
            status='present'
        )
        Attendance.objects.create(
            employee=self.employee,
            date=timezone.datetime(2026, 8, 6).date(),
            status='half_day'
        )
        Attendance.objects.create(
            employee=self.employee,
            date=timezone.datetime(2026, 8, 7).date(),
            status='absent'
        )

        leave_type = LeaveType.objects.create(name="Unpaid Leave", code="UNPAID", is_paid=False)
        LeaveRequest.objects.create(
            employee=self.employee,
            leave_type=leave_type,
            start_date=timezone.datetime(2026, 8, 10).date(),
            end_date=timezone.datetime(2026, 8, 12).date(),
            total_days=3,
            reason="Personal",
            status="approved"
        )

        summary = get_month_attendance_summary(self.employee, 8, 2026)
        self.assertEqual(summary['working_days'], 31)
        self.assertGreater(summary['present_days'], Decimal("0.0"))
        self.assertGreater(summary['lwp_days'], Decimal("0.0"))
