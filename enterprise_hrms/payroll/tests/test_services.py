"""
Module 11: Comprehensive service tests for the PayrollService layer.
Covers all service methods, business rules, validators, calculations,
attendance/leave integration, reports, and export functionality.
Target: 90%+ code coverage.
"""
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
    calculate_gross_salary,
    calculate_base_deductions,
    calculate_lwp_deduction,
    calculate_overtime_pay,
    calculate_net_salary,
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
    """Tests for all PayrollService methods."""

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
        """Tests create, update, delete salary structure via service layer."""
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

    def test_create_salary_structure_invalid_employee(self):
        """Service should raise NotFound for non-existent employee."""
        with self.assertRaises(NotFound):
            PayrollService.create_salary_structure(employee_id=99999, data={"basic_salary": "1000.00"})

    def test_create_salary_structure_marks_previous_inactive(self):
        """Creating a new active salary structure deactivates previous active ones."""
        # First structure is already active from setUp
        new_structure = PayrollService.create_salary_structure(
            employee_id=self.employee.id,
            data={
                "basic_salary": Decimal("5000.00"),
                "effective_from": timezone.now().date(),
                "status": "active"
            }
        )
        self.structure.refresh_from_db()
        self.assertEqual(self.structure.status, "inactive")
        self.assertEqual(new_structure.status, "active")

    def test_create_salary_structure_inactive_does_not_deactivate(self):
        """Creating an inactive structure leaves existing active structure."""
        inactive_struct = PayrollService.create_salary_structure(
            employee_id=self.employee.id,
            data={
                "basic_salary": Decimal("5000.00"),
                "effective_from": timezone.now().date(),
                "status": "inactive"
            }
        )
        self.structure.refresh_from_db()
        self.assertEqual(self.structure.status, "active")
        self.assertEqual(inactive_struct.status, "inactive")

    def test_calculate_salary_and_deductions(self):
        """Tests salary calculation for gross, base deductions, and net."""
        breakdown = PayrollService.calculate_salary(self.employee, month=8, year=2026)
        self.assertEqual(breakdown['gross_salary'], Decimal("6000.00"))
        self.assertEqual(breakdown['base_deductions'], Decimal("1000.00"))
        self.assertEqual(breakdown['net_salary'], Decimal("5000.00"))

        deductions = PayrollService.calculate_deductions(self.structure, lwp_days=2, working_days=30)
        self.assertEqual(deductions, Decimal("1400.00"))

        overtime = calculate_overtime_pay(Decimal("6000.00"), overtime_hours=10, working_days=30)
        self.assertGreater(overtime, Decimal("0.00"))

    def test_calculate_salary_with_explicit_structure(self):
        """calculate_salary accepts an explicit salary_structure argument."""
        breakdown = PayrollService.calculate_salary(
            self.employee, month=8, year=2026,
            salary_structure=self.structure
        )
        self.assertIn('gross_salary', breakdown)
        self.assertIn('net_salary', breakdown)

    def test_payroll_workflow_create_approve_release(self):
        """Full payroll workflow: create → approve → release."""
        run = PayrollService.create_payroll_run(
            payroll_month=8,
            payroll_year=2026,
            processed_by=self.hr_user,
            remarks="August Payroll"
        )
        self.assertEqual(run.status, 'draft')
        self.assertTrue(Payslip.objects.filter(payroll_run=run, employee=self.employee).exists())

        # Cannot create duplicate payroll run for same month
        with self.assertRaises(ValidationError):
            PayrollService.create_payroll_run(payroll_month=8, payroll_year=2026, processed_by=self.hr_user)

        # Cannot release before approval
        with self.assertRaises(ValidationError):
            PayrollService.release_payroll(run.id)

        approved_run = PayrollService.approve_payroll(run.id, approved_by=self.hr_user)
        self.assertEqual(approved_run.status, 'approved')
        self.assertEqual(approved_run.approved_by, self.hr_user)
        self.assertIsNotNone(approved_run.approved_at)

        released_run = PayrollService.release_payroll(run.id)
        self.assertEqual(released_run.status, 'released')
        run.refresh_from_db()

        # Cannot approve released payroll
        with self.assertRaises(ValidationError):
            PayrollService.approve_payroll(run.id, approved_by=self.hr_user)

        # Cannot regenerate payslip for released payroll
        with self.assertRaises(ValidationError):
            PayrollService.generate_payslip(self.employee, run)

    def test_approve_payroll_not_found(self):
        """Approving non-existent payroll run raises NotFound."""
        with self.assertRaises(NotFound):
            PayrollService.approve_payroll(99999, approved_by=self.hr_user)

    def test_release_payroll_not_found(self):
        """Releasing non-existent payroll run raises NotFound."""
        with self.assertRaises(NotFound):
            PayrollService.release_payroll(99999)

    def test_payroll_summary_service(self):
        """payroll_summary() delegates to reports module correctly."""
        run = PayrollService.create_payroll_run(payroll_month=9, payroll_year=2026, processed_by=self.hr_user)
        summary = PayrollService.payroll_summary(payroll_run_id=run.id)
        self.assertIn('total_employees_paid', summary)
        self.assertIn('gross_payroll', summary)
        self.assertIn('net_payroll', summary)

    def test_get_dashboard_analytics(self):
        """get_dashboard_analytics() returns expected keys."""
        analytics = PayrollService.get_dashboard_analytics()
        self.assertIn('current_payroll_status', analytics)
        self.assertIn('employees_processed', analytics)
        self.assertIn('pending_payslips', analytics)
        self.assertIn('total_payroll_cost', analytics)
        self.assertIn('department_payroll_summary', analytics)

    def test_get_dashboard_analytics_no_runs(self):
        """Dashboard analytics works correctly when no payroll runs exist."""
        analytics = PayrollService.get_dashboard_analytics()
        self.assertEqual(analytics['current_payroll_status'], 'No Runs')
        self.assertIsNone(analytics['latest_payroll_run'])

    def test_validators_direct(self):
        """Tests each validator function directly."""
        # validate_payroll_approval_for_release with None
        with self.assertRaises(ValidationError):
            validate_payroll_approval_for_release(None)

        # validate_payroll_approval_for_release with unapproved run
        unapproved_run = PayrollRun.objects.create(payroll_month=1, payroll_year=2030, status='draft')
        with self.assertRaises(ValidationError):
            validate_payroll_approval_for_release(unapproved_run)

        # validate_non_negative_net_salary
        with self.assertRaises(ValidationError):
            validate_non_negative_net_salary(Decimal("-10.00"))

        # validate_non_negative_net_salary passes for zero
        validate_non_negative_net_salary(Decimal("0.00"))  # no exception

        # validate_salary_structure_exists for employee without structure
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

        # validate_salary_structure_exists returns structure when it exists
        structure = validate_salary_structure_exists(self.employee)
        self.assertIsNotNone(structure)

    def test_validate_single_payroll_run_per_month(self):
        """Validator allows exclusion of a specific run (for update scenarios)."""
        run = PayrollRun.objects.create(payroll_month=5, payroll_year=2026, status='draft')
        # Should not raise when excluding the same run
        validate_single_payroll_run_per_month(5, 2026, exclude_id=run.id)
        # Should raise when not excluding
        with self.assertRaises(ValidationError):
            validate_single_payroll_run_per_month(5, 2026)

    def test_validate_payroll_run_not_released(self):
        """Validator raises if run is released, passes otherwise."""
        released_run = PayrollRun.objects.create(payroll_month=4, payroll_year=2026, status='released')
        with self.assertRaises(ValidationError):
            validate_payroll_run_not_released(released_run)

        draft_run = PayrollRun.objects.create(payroll_month=6, payroll_year=2026, status='draft')
        validate_payroll_run_not_released(draft_run)  # no exception

        # None should not raise
        validate_payroll_run_not_released(None)  # no exception

    def test_reports_generation_and_export(self):
        """Generates payroll reports in all formats (PDF, Excel, CSV)."""
        run = PayrollService.create_payroll_run(payroll_month=9, payroll_year=2026, processed_by=self.hr_user)
        summary = get_payroll_summary_report(month=9, year=2026)
        self.assertEqual(summary['total_employees_paid'], 1)

        dept_report = get_department_payroll_report(month=9, year=2026)
        self.assertTrue(len(dept_report) >= 1)

        history = get_employee_salary_history(self.employee.id)
        self.assertTrue(len(history) >= 1)
        self.assertIn('payslip_id', history[0])
        self.assertIn('month', history[0])
        self.assertIn('year', history[0])

        pdf_bytes = export_payroll_report_pdf(9, 2026)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 0)

        excel_bytes = export_payroll_register_excel(9, 2026)
        self.assertIsInstance(excel_bytes, bytes)
        self.assertGreater(len(excel_bytes), 0)

        csv_bytes = export_payroll_transactions_csv(9, 2026)
        self.assertIsInstance(csv_bytes, str)
        self.assertGreater(len(csv_bytes), 0)
        self.assertIn("Employee ID", csv_bytes)

    def test_report_summary_with_payroll_run_id(self):
        """get_payroll_summary_report works with explicit run ID."""
        run = PayrollService.create_payroll_run(payroll_month=10, payroll_year=2026, processed_by=self.hr_user)
        summary = get_payroll_summary_report(payroll_run_id=run.id)
        self.assertEqual(summary['total_employees_paid'], 1)

    def test_report_summary_all_payslips(self):
        """get_payroll_summary_report with no filters returns all payslips."""
        PayrollService.create_payroll_run(payroll_month=11, payroll_year=2026, processed_by=self.hr_user)
        summary = get_payroll_summary_report()
        self.assertGreaterEqual(summary['total_employees_paid'], 1)

    def test_export_excel_all_months(self):
        """export_payroll_register_excel with no month/year returns all payslips."""
        PayrollService.create_payroll_run(payroll_month=12, payroll_year=2026, processed_by=self.hr_user)
        excel_bytes = export_payroll_register_excel()
        self.assertGreater(len(excel_bytes), 0)

    def test_export_csv_all_months(self):
        """export_payroll_transactions_csv with no month/year returns all payslips."""
        PayrollService.create_payroll_run(payroll_month=7, payroll_year=2026, processed_by=self.hr_user)
        csv_bytes = export_payroll_transactions_csv()
        self.assertGreater(len(csv_bytes), 0)

    def test_attendance_and_leave_integration(self):
        """Attendance and leave records affect payroll calculations correctly."""
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

    def test_paid_leave_does_not_count_as_lwp(self):
        """Approved paid leave does not add to LWP days."""
        leave_type = LeaveType.objects.create(name="Annual Leave", code="AL", is_paid=True)
        LeaveRequest.objects.create(
            employee=self.employee,
            leave_type=leave_type,
            start_date=timezone.datetime(2026, 8, 15).date(),
            end_date=timezone.datetime(2026, 8, 15).date(),
            total_days=1,
            reason="Vacation",
            status="approved"
        )
        summary = get_month_attendance_summary(self.employee, 8, 2026)
        # leave_days should include 1 day
        self.assertEqual(summary['leave_days'], Decimal("1.0"))
        # But lwp_days should NOT include it (paid leave)
        self.assertEqual(summary['lwp_days'], Decimal("0.0"))

    def test_employee_with_no_attendance_records(self):
        """Attendance summary works when employee has no records at all."""
        summary = get_month_attendance_summary(self.employee, 1, 2026)
        self.assertEqual(summary['present_days'], Decimal("0.0"))
        self.assertEqual(summary['leave_days'], Decimal("0.0"))
        self.assertEqual(summary['lwp_days'], Decimal("0.0"))
        self.assertEqual(summary['overtime_hours'], Decimal("0.00"))


class CalculationsTest(TestCase):
    """Unit tests for each calculation function."""

    def setUp(self):
        self.dept = Department.objects.create(name="Engineering", code="ENGT")
        self.employee = Employee.objects.create(
            employee_id="EMP200",
            first_name="Bob",
            last_name="Builder",
            email="bob.builder@example.com",
            dob="1985-01-01",
            gender="male",
            department=self.dept,
            designation="Engineer",
            salary=Decimal("5000.00"),
            joining_date="2020-01-01",
            status="active"
        )
        self.structure = SalaryStructure.objects.create(
            employee=self.employee,
            basic_salary=Decimal("3000.00"),
            house_rent_allowance=Decimal("800.00"),
            special_allowance=Decimal("400.00"),
            travel_allowance=Decimal("200.00"),
            medical_allowance=Decimal("100.00"),
            provident_fund=Decimal("300.00"),
            professional_tax=Decimal("100.00"),
            income_tax=Decimal("200.00"),
            other_deductions=Decimal("50.00"),
            effective_from="2025-01-01",
            status="active"
        )

    def test_calculate_gross_salary(self):
        gross = calculate_gross_salary(self.structure)
        self.assertEqual(gross, Decimal("4500.00"))

    def test_calculate_base_deductions(self):
        deductions = calculate_base_deductions(self.structure)
        self.assertEqual(deductions, Decimal("650.00"))

    def test_calculate_lwp_deduction_zero_days(self):
        deduction = calculate_lwp_deduction(Decimal("4500.00"), lwp_days=0, working_days=30)
        self.assertEqual(deduction, Decimal("0.00"))

    def test_calculate_lwp_deduction_zero_working_days(self):
        deduction = calculate_lwp_deduction(Decimal("4500.00"), lwp_days=2, working_days=0)
        self.assertEqual(deduction, Decimal("0.00"))

    def test_calculate_lwp_deduction_valid(self):
        # Daily rate = 4500/30 = 150; 2 days = 300
        deduction = calculate_lwp_deduction(Decimal("4500.00"), lwp_days=2, working_days=30)
        self.assertEqual(deduction, Decimal("300.00"))

    def test_calculate_overtime_pay_zero_hours(self):
        overtime = calculate_overtime_pay(Decimal("4500.00"), overtime_hours=0, working_days=30)
        self.assertEqual(overtime, Decimal("0.00"))

    def test_calculate_overtime_pay_zero_working_days(self):
        overtime = calculate_overtime_pay(Decimal("4500.00"), overtime_hours=5, working_days=0)
        self.assertEqual(overtime, Decimal("0.00"))

    def test_calculate_overtime_pay_valid(self):
        # Hourly rate = 4500 / (30 * 8) = 18.75; overtime = 18.75 * 1.5 * 5 = 140.625
        overtime = calculate_overtime_pay(Decimal("4500.00"), overtime_hours=5, working_days=30)
        self.assertGreater(overtime, Decimal("0.00"))

    def test_calculate_net_salary_positive(self):
        net = calculate_net_salary(Decimal("4500.00"), Decimal("650.00"), Decimal("100.00"))
        self.assertEqual(net, Decimal("3950.00"))

    def test_calculate_net_salary_floored_at_zero(self):
        net = calculate_net_salary(Decimal("100.00"), Decimal("5000.00"))
        self.assertEqual(net, Decimal("0.00"))

    def test_calculate_full_salary_breakdown_structure(self):
        breakdown = calculate_full_salary_breakdown(self.structure, month=8, year=2026)
        self.assertIn('gross_salary', breakdown)
        self.assertIn('total_deductions', breakdown)
        self.assertIn('net_salary', breakdown)
        self.assertIn('working_days', breakdown)
        self.assertIn('present_days', breakdown)
        self.assertIn('leave_days', breakdown)
        self.assertIn('lwp_days', breakdown)
        self.assertIn('overtime_hours', breakdown)
        self.assertIn('basic_salary', breakdown)
        self.assertIn('house_rent_allowance', breakdown)
        self.assertIn('special_allowance', breakdown)
        self.assertIn('travel_allowance', breakdown)
        self.assertIn('medical_allowance', breakdown)
        self.assertIn('provident_fund', breakdown)
        self.assertIn('professional_tax', breakdown)
        self.assertIn('income_tax', breakdown)
        self.assertIn('other_deductions', breakdown)
        self.assertEqual(breakdown['gross_salary'], Decimal("4500.00"))

    def test_calculate_full_salary_breakdown_with_custom_attendance(self):
        """Can pass pre-computed attendance_summary to calculate_full_salary_breakdown."""
        attendance_summary = {
            'working_days': 30,
            'present_days': Decimal("25.0"),
            'leave_days': Decimal("2.0"),
            'lwp_days': Decimal("3.0"),
            'overtime_hours': Decimal("5.00")
        }
        breakdown = calculate_full_salary_breakdown(
            self.structure, month=8, year=2026,
            attendance_summary=attendance_summary
        )
        self.assertEqual(breakdown['working_days'], 30)
        self.assertEqual(breakdown['present_days'], Decimal("25.0"))
        self.assertGreater(breakdown['lwp_deduction'], Decimal("0.00"))


class PDFGeneratorTest(TestCase):
    """Tests for payslip PDF generation."""

    def setUp(self):
        self.dept = Department.objects.create(name="IT", code="ITC")
        self.employee = Employee.objects.create(
            employee_id="EMP300",
            first_name="Carol",
            last_name="White",
            email="carol.white@example.com",
            dob="1988-03-15",
            gender="female",
            department=self.dept,
            designation="Analyst",
            salary=Decimal("5500.00"),
            joining_date="2021-09-01",
            status="active"
        )
        self.hr_user = User.objects.create_user(
            username="hr_pdf",
            email="hr_pdf@example.com",
            password="password123",
            role="hr"
        )
        self.structure = PayrollService.create_salary_structure(
            employee_id=self.employee.id,
            data={
                "basic_salary": Decimal("4000.00"),
                "house_rent_allowance": Decimal("1000.00"),
                "provident_fund": Decimal("400.00"),
                "effective_from": timezone.now().date(),
                "status": "active"
            }
        )

    def test_payslip_pdf_generated_and_saved(self):
        """PDF is generated and saved to media/payslips/ on payroll run."""
        run = PayrollService.create_payroll_run(
            payroll_month=3, payroll_year=2026,
            processed_by=self.hr_user
        )
        payslip = Payslip.objects.get(payroll_run=run, employee=self.employee)
        # PDF path should be set after generation
        self.assertTrue(bool(payslip.pdf_path))
        self.assertIn("payslips/", payslip.pdf_path.name)
        self.assertIn(self.employee.employee_id, payslip.pdf_path.name)

    def test_payslip_pdf_content_valid(self):
        """Generated PDF starts with PDF header bytes."""
        from enterprise_hrms.payroll.pdf_generator import generate_payslip_pdf
        run = PayrollService.create_payroll_run(
            payroll_month=4, payroll_year=2026,
            processed_by=self.hr_user
        )
        payslip = Payslip.objects.get(payroll_run=run, employee=self.employee)
        pdf_content = generate_payslip_pdf(payslip)
        self.assertIsInstance(pdf_content, bytes)
        # PDF magic bytes
        self.assertTrue(pdf_content.startswith(b'%PDF'))
