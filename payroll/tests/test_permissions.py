from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from enterprise_hrms.employees.models import Employee
from enterprise_hrms.departments.models import Department
from enterprise_hrms.payroll.models import PayrollRun, Payslip
from enterprise_hrms.payroll.services import PayrollService

User = get_user_model()


class PayrollPermissionsTest(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="Password123!",
            role="admin"
        )
        self.hr_user = User.objects.create_user(
            username="hr",
            email="hr@example.com",
            password="Password123!",
            role="hr"
        )
        self.emp1_user = User.objects.create_user(
            username="emp1",
            email="emp1@example.com",
            password="Password123!",
            role="employee"
        )
        self.emp2_user = User.objects.create_user(
            username="emp2",
            email="emp2@example.com",
            password="Password123!",
            role="employee"
        )

        self.dept = Department.objects.create(name="IT", code="ITD")

        self.employee1 = Employee.objects.create(
            employee_id="EMP301",
            first_name="Charlie",
            last_name="Brown",
            email="charlie@example.com",
            dob="1995-03-20",
            gender="male",
            department=self.dept,
            designation="Dev",
            salary=Decimal("4000.00"),
            joining_date="2023-01-01",
            status="active",
            user=self.emp1_user
        )

        self.employee2 = Employee.objects.create(
            employee_id="EMP302",
            first_name="Diana",
            last_name="Prince",
            email="diana@example.com",
            dob="1993-07-15",
            gender="female",
            department=self.dept,
            designation="QA",
            salary=Decimal("4500.00"),
            joining_date="2023-02-01",
            status="active",
            user=self.emp2_user
        )

        PayrollService.create_salary_structure(
            employee_id=self.employee1.id,
            data={"basic_salary": Decimal("4000.00")}
        )
        PayrollService.create_salary_structure(
            employee_id=self.employee2.id,
            data={"basic_salary": Decimal("4500.00")}
        )

        self.run = PayrollService.create_payroll_run(payroll_month=12, payroll_year=2026, processed_by=self.hr_user)
        self.payslip1 = Payslip.objects.get(payroll_run=self.run, employee=self.employee1)
        self.payslip2 = Payslip.objects.get(payroll_run=self.run, employee=self.employee2)

    def test_employee_cannot_create_salary_structure(self):
        self.client.force_authenticate(user=self.emp1_user)
        response = self.client.post("/api/v1/payroll/salary-structure/", {"employee": self.employee1.id, "basic_salary": "5000.00"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_cannot_create_payroll_run(self):
        self.client.force_authenticate(user=self.emp1_user)
        response = self.client.post("/api/v1/payroll/run/", {"payroll_month": 1, "payroll_year": 2027})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_cannot_access_other_employee_payslip(self):
        self.client.force_authenticate(user=self.emp1_user)
        # Attempting to access emp2's payslip should be filtered out / returned as 404
        response = self.client.get(f"/api/v1/payroll/payslips/{self.payslip2.id}/")
        self.assertIn(response.status_code, [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN])

    def test_hr_and_admin_full_access(self):
        self.client.force_authenticate(user=self.hr_user)
        response = self.client.get("/api/v1/payroll/run/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get("/api/v1/payroll/run/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
