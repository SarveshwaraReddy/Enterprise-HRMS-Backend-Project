from decimal import Decimal
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from enterprise_hrms.employees.models import Employee
from enterprise_hrms.departments.models import Department
from enterprise_hrms.payroll.models import SalaryStructure, PayrollRun, Payslip
from enterprise_hrms.payroll.services import PayrollService

User = get_user_model()


class PayrollAPITest(APITestCase):
    def setUp(self):
        self.hr_user = User.objects.create_user(
            username="hr_admin",
            email="hr_admin@example.com",
            password="Password123!",
            role="hr"
        )
        self.emp_user = User.objects.create_user(
            username="emp_user",
            email="emp_user@example.com",
            password="Password123!",
            role="employee"
        )

        self.dept = Department.objects.create(name="Finance", code="FIN")

        self.employee = Employee.objects.create(
            employee_id="EMP201",
            first_name="Bob",
            last_name="Marley",
            email="bob@example.com",
            dob="1985-02-15",
            gender="male",
            department=self.dept,
            designation="Financial Analyst",
            salary=Decimal("7000.00"),
            joining_date="2021-06-01",
            status="active",
            user=self.emp_user
        )

        self.structure = PayrollService.create_salary_structure(
            employee_id=self.employee.id,
            data={
                "basic_salary": Decimal("5000.00"),
                "house_rent_allowance": Decimal("1200.00"),
                "special_allowance": Decimal("500.00"),
                "travel_allowance": Decimal("200.00"),
                "medical_allowance": Decimal("100.00"),
                "provident_fund": Decimal("500.00"),
                "professional_tax": Decimal("200.00"),
                "income_tax": Decimal("400.00"),
                "other_deductions": Decimal("100.00"),
                "effective_from": timezone.now().date(),
                "status": "active"
            }
        )

    def test_salary_structure_api_crud(self):
        self.client.force_authenticate(user=self.hr_user)

        response = self.client.get("/api/v1/payroll/salary-structure/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post("/api/v1/payroll/salary-structure/", {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        data = {
            "employee": self.employee.id,
            "basic_salary": "5500.00",
            "house_rent_allowance": "1200.00",
            "effective_from": "2026-01-01",
            "status": "active"
        }
        response = self.client.post("/api/v1/payroll/salary-structure/", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        struct_id = response.data['id']

        update_data = {"basic_salary": "6000.00"}
        response = self.client.put(f"/api/v1/payroll/salary-structure/{struct_id}/", update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.delete(f"/api/v1/payroll/salary-structure/{struct_id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_payroll_run_and_approval_release_api(self):
        self.client.force_authenticate(user=self.hr_user)

        data = {"payroll_month": 10, "payroll_year": 2026, "remarks": "October Payroll"}
        response = self.client.post("/api/v1/payroll/run/", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        run_id = response.data['id']

        response = self.client.put(f"/api/v1/payroll/run/{run_id}/approve/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'approved')

        response = self.client.put(f"/api/v1/payroll/run/{run_id}/release/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'released')

    def test_payslip_and_download_api(self):
        run = PayrollService.create_payroll_run(payroll_month=11, payroll_year=2026, processed_by=self.hr_user)
        payslip = Payslip.objects.get(payroll_run=run, employee=self.employee)

        self.client.force_authenticate(user=self.emp_user)

        response = self.client.get("/api/v1/payroll/payslips/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(f"/api/v1/payroll/payslips/{payslip.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(f"/api/v1/payroll/payslips/{payslip.id}/download/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_dashboard_and_reports_api(self):
        self.client.force_authenticate(user=self.hr_user)

        # Dashboard
        response = self.client.get("/api/v1/payroll/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

        # Summary Report
        response = self.client.get("/api/v1/payroll/reports/summary/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Department Report
        response = self.client.get("/api/v1/payroll/reports/department/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Employee Salary History
        response = self.client.get("/api/v1/payroll/reports/history/", data={"employee_id": self.employee.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Export CSV
        response = self.client.get("/api/v1/payroll/reports/export/", data={"format": "csv", "month": 11, "year": 2026})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/csv')

        # Export Excel
        response = self.client.get("/api/v1/payroll/reports/export/", data={"format": "excel", "month": 11, "year": 2026})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('spreadsheetml', response['Content-Type'])

        # Export PDF
        response = self.client.get("/api/v1/payroll/reports/export/", data={"format": "pdf", "month": 11, "year": 2026})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')

        # Unsupported export format
        response = self.client.get("/api/v1/payroll/reports/export/", data={"format": "invalid"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Invalid report type
        response = self.client.get("/api/v1/payroll/reports/unknown_type/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_employee_permission_denied_on_reports(self):
        self.client.force_authenticate(user=self.emp_user)

        response = self.client.get("/api/v1/payroll/reports/summary/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.get("/api/v1/payroll/reports/department/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.get("/api/v1/payroll/reports/export/", data={"format": "csv"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
