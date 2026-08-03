from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from django.db import IntegrityError
from enterprise_hrms.employees.models import Employee
from enterprise_hrms.departments.models import Department
from enterprise_hrms.payroll.models import SalaryStructure, PayrollRun, Payslip


class PayrollModelsTest(TestCase):
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

        self.assertEqual(structure.gross_salary, Decimal("5800.00"))
        self.assertEqual(structure.total_deductions, Decimal("850.00"))
        self.assertEqual(structure.net_salary, Decimal("4950.00"))
        self.assertIn("Salary Structure for", str(structure))

    def test_payroll_run_creation_and_uniqueness(self):
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

    def test_payslip_creation_and_uniqueness(self):
        run = PayrollRun.objects.create(payroll_month=9, payroll_year=2026, status="draft")
        payslip = Payslip.objects.create(
            employee=self.employee,
            payroll_run=run,
            gross_salary=Decimal("5000.00"),
            total_deductions=Decimal("500.00"),
            net_salary=Decimal("4500.00"),
            working_days=30,
            present_days=Decimal("28.0"),
            leave_days=Decimal("2.0")
        )

        self.assertIn("Payslip for", str(payslip))
        with self.assertRaises(IntegrityError):
            Payslip.objects.create(
                employee=self.employee,
                payroll_run=run,
                gross_salary=Decimal("5000.00"),
                total_deductions=Decimal("500.00"),
                net_salary=Decimal("4500.00")
            )
