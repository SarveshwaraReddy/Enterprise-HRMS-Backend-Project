"""
Module 11: Comprehensive model tests for SalaryStructure, PayrollRun, and Payslip.
Tests all model fields, properties, constraints, and string representations.
"""
from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from django.db import IntegrityError
from enterprise_hrms.employees.models import Employee
from enterprise_hrms.departments.models import Department
from enterprise_hrms.payroll.models import SalaryStructure, PayrollRun, Payslip


class SalaryStructureModelTest(TestCase):
    """Tests for SalaryStructure model: creation, properties, constraints."""

    def setUp(self):
        self.dept = Department.objects.create(name="Engineering", code="ENG")
        self.employee = Employee.objects.create(
            employee_id="EMP001",
            first_name="John",
            last_name="Doe",
            email="john.doe@example.com",
            dob="1990-01-01",
            gender="male",
            department=self.dept,
            designation="Developer",
            salary=Decimal("5000.00"),
            joining_date="2023-01-01",
            status="active"
        )

    def test_salary_structure_creation_and_properties(self):
        """Test gross_salary, total_deductions, net_salary computed properties."""
        structure = SalaryStructure.objects.create(
            employee=self.employee,
            basic_salary=Decimal("4000.00"),
            house_rent_allowance=Decimal("1000.00"),
            special_allowance=Decimal("500.00"),
            travel_allowance=Decimal("200.00"),
            medical_allowance=Decimal("100.00"),
            provident_fund=Decimal("400.00"),
            professional_tax=Decimal("150.00"),
            income_tax=Decimal("250.00"),
            other_deductions=Decimal("50.00"),
            effective_from=timezone.now().date(),
            status="active"
        )
        # Gross = 4000 + 1000 + 500 + 200 + 100 = 5800
        self.assertEqual(structure.gross_salary, Decimal("5800.00"))
        # Deductions = 400 + 150 + 250 + 50 = 850
        self.assertEqual(structure.total_deductions, Decimal("850.00"))
        # Net = 5800 - 850 = 4950
        self.assertEqual(structure.net_salary, Decimal("4950.00"))
        self.assertIn("Salary Structure for", str(structure))

    def test_net_salary_cannot_be_negative(self):
        """Net salary is floored at 0 when deductions exceed gross."""
        structure = SalaryStructure.objects.create(
            employee=self.employee,
            basic_salary=Decimal("1000.00"),
            provident_fund=Decimal("2000.00"),  # deductions > gross
            professional_tax=Decimal("0.00"),
            income_tax=Decimal("0.00"),
            other_deductions=Decimal("0.00"),
            effective_from=timezone.now().date(),
            status="active"
        )
        self.assertEqual(structure.net_salary, Decimal("0.00"))

    def test_salary_structure_defaults(self):
        """Test that optional allowance/deduction fields default to 0."""
        structure = SalaryStructure.objects.create(
            employee=self.employee,
            basic_salary=Decimal("3000.00"),
            effective_from=timezone.now().date(),
        )
        self.assertEqual(structure.house_rent_allowance, Decimal("0.00"))
        self.assertEqual(structure.special_allowance, Decimal("0.00"))
        self.assertEqual(structure.travel_allowance, Decimal("0.00"))
        self.assertEqual(structure.medical_allowance, Decimal("0.00"))
        self.assertEqual(structure.provident_fund, Decimal("0.00"))
        self.assertEqual(structure.professional_tax, Decimal("0.00"))
        self.assertEqual(structure.income_tax, Decimal("0.00"))
        self.assertEqual(structure.other_deductions, Decimal("0.00"))
        self.assertEqual(structure.status, "active")

    def test_salary_structure_status_choices(self):
        """Test active/inactive status values."""
        structure = SalaryStructure.objects.create(
            employee=self.employee,
            basic_salary=Decimal("3000.00"),
            effective_from=timezone.now().date(),
            status="inactive"
        )
        self.assertEqual(structure.status, "inactive")

    def test_salary_structure_ordering(self):
        """Multiple structures ordered by effective_from desc."""
        s1 = SalaryStructure.objects.create(
            employee=self.employee,
            basic_salary=Decimal("3000.00"),
            effective_from="2025-01-01",
        )
        s2 = SalaryStructure.objects.create(
            employee=self.employee,
            basic_salary=Decimal("4000.00"),
            effective_from="2026-01-01",
        )
        structures = list(SalaryStructure.objects.filter(employee=self.employee))
        self.assertEqual(structures[0], s2)  # newer first
        self.assertEqual(structures[1], s1)

    def test_salary_structure_str_representation(self):
        structure = SalaryStructure.objects.create(
            employee=self.employee,
            basic_salary=Decimal("3000.00"),
            effective_from="2026-01-01",
        )
        self.assertIn("John Doe", str(structure))
        self.assertIn("2026-01-01", str(structure))


class PayrollRunModelTest(TestCase):
    """Tests for PayrollRun model: creation, uniqueness, status choices."""

    def test_payroll_run_creation_and_uniqueness(self):
        """Test that only one PayrollRun can exist per month/year."""
        run1 = PayrollRun.objects.create(
            payroll_month=8,
            payroll_year=2026,
            status="draft"
        )
        self.assertEqual(str(run1), "Payroll Run 8/2026 (Draft)")

        with self.assertRaises(IntegrityError):
            PayrollRun.objects.create(
                payroll_month=8,
                payroll_year=2026,
                status="draft"
            )

    def test_payroll_run_status_choices(self):
        """Test all four status values."""
        for status_val in ['draft', 'processing', 'approved', 'released']:
            run = PayrollRun.objects.create(
                payroll_month=PayrollRun.objects.count() + 1,
                payroll_year=2026,
                status=status_val
            )
            self.assertEqual(run.status, status_val)

    def test_payroll_run_ordering(self):
        """PayrollRun ordered by year then month desc."""
        run1 = PayrollRun.objects.create(payroll_month=1, payroll_year=2026)
        run2 = PayrollRun.objects.create(payroll_month=6, payroll_year=2026)
        run3 = PayrollRun.objects.create(payroll_month=1, payroll_year=2025)
        runs = list(PayrollRun.objects.all())
        self.assertEqual(runs[0], run2)  # 2026/6 first
        self.assertEqual(runs[1], run1)  # 2026/1 second
        self.assertEqual(runs[2], run3)  # 2025/1 last

    def test_payroll_run_nullable_fields(self):
        """processed_by, approved_by etc. are nullable."""
        run = PayrollRun.objects.create(payroll_month=3, payroll_year=2026)
        self.assertIsNone(run.processed_by)
        self.assertIsNone(run.approved_by)
        self.assertIsNone(run.processed_at)
        self.assertIsNone(run.approved_at)
        self.assertIsNone(run.remarks)

    def test_payroll_run_different_years_allowed(self):
        """Same month in different years should work."""
        run1 = PayrollRun.objects.create(payroll_month=1, payroll_year=2024)
        run2 = PayrollRun.objects.create(payroll_month=1, payroll_year=2025)
        self.assertNotEqual(run1, run2)


class PayslipModelTest(TestCase):
    """Tests for Payslip model: creation, uniqueness, and str rep."""

    def setUp(self):
        self.dept = Department.objects.create(name="Finance", code="FIN")
        self.employee = Employee.objects.create(
            employee_id="EMP002",
            first_name="Jane",
            last_name="Smith",
            email="jane.smith@example.com",
            dob="1991-05-10",
            gender="female",
            department=self.dept,
            designation="Analyst",
            salary=Decimal("4500.00"),
            joining_date="2022-06-01",
            status="active"
        )
        self.run = PayrollRun.objects.create(payroll_month=9, payroll_year=2026, status="draft")

    def test_payslip_creation_and_uniqueness(self):
        """Test payslip creation and unique_together constraint."""
        payslip = Payslip.objects.create(
            employee=self.employee,
            payroll_run=self.run,
            gross_salary=Decimal("5000.00"),
            total_deductions=Decimal("500.00"),
            net_salary=Decimal("4500.00"),
            working_days=30,
            present_days=Decimal("28.0"),
            leave_days=Decimal("2.0")
        )
        self.assertIn("Payslip for", str(payslip))
        self.assertIn("Jane Smith", str(payslip))

        with self.assertRaises(IntegrityError):
            Payslip.objects.create(
                employee=self.employee,
                payroll_run=self.run,
                gross_salary=Decimal("5000.00"),
                total_deductions=Decimal("500.00"),
                net_salary=Decimal("4500.00")
            )

    def test_payslip_defaults(self):
        """Test default field values."""
        payslip = Payslip.objects.create(
            employee=self.employee,
            payroll_run=self.run
        )
        self.assertEqual(payslip.gross_salary, Decimal("0.00"))
        self.assertEqual(payslip.total_deductions, Decimal("0.00"))
        self.assertEqual(payslip.net_salary, Decimal("0.00"))
        self.assertEqual(payslip.working_days, 0)
        self.assertEqual(payslip.present_days, Decimal("0.0"))
        self.assertEqual(payslip.leave_days, Decimal("0.0"))
        self.assertEqual(payslip.overtime_hours, Decimal("0.00"))
        self.assertIsNone(payslip.pdf_path.name)

    def test_payslip_ordering(self):
        """Payslips ordered by generated_at desc."""
        run2 = PayrollRun.objects.create(payroll_month=10, payroll_year=2026)
        slip1 = Payslip.objects.create(employee=self.employee, payroll_run=self.run)
        slip2 = Payslip.objects.create(employee=self.employee, payroll_run=run2)
        slips = list(Payslip.objects.filter(employee=self.employee))
        # most recently generated should be first
        self.assertEqual(slips[0], slip2)
