"""
Module 11: Comprehensive API tests for all payroll REST endpoints.
Covers: Salary Structure CRUD, Payroll Run lifecycle, Payslip access,
Dashboard, Reports (summary, department, history, export), and edge cases.
"""
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

    # ─── Salary Structure API ───────────────────────────────────────────────

    def test_salary_structure_api_crud(self):
        self.client.force_authenticate(user=self.hr_user)

        response = self.client.get("/api/v1/payroll/salary-structure/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # POST without employee ID returns 400
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

    def test_salary_structure_list_as_employee(self):
        """Employees are blocked from salary structure list by IsPayrollAdmin permission."""
        self.client.force_authenticate(user=self.emp_user)
        response = self.client.get("/api/v1/payroll/salary-structure/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_salary_structure_detail_as_hr(self):
        """HR can retrieve a specific salary structure."""
        self.client.force_authenticate(user=self.hr_user)
        response = self.client.get(f"/api/v1/payroll/salary-structure/{self.structure.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.structure.id)

    # ─── Payroll Run API ────────────────────────────────────────────────────

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

    def test_payroll_run_list_filtered_by_month(self):
        """Payroll run list supports filtering by month/year/status."""
        self.client.force_authenticate(user=self.hr_user)
        PayrollService.create_payroll_run(payroll_month=8, payroll_year=2026, processed_by=self.hr_user)
        response = self.client.get("/api/v1/payroll/run/?payroll_month=8&payroll_year=2026")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_payroll_run_approve_via_post(self):
        """Approve endpoint also responds to POST method."""
        self.client.force_authenticate(user=self.hr_user)
        data = {"payroll_month": 6, "payroll_year": 2026}
        response = self.client.post("/api/v1/payroll/run/", data)
        run_id = response.data['id']
        response = self.client.post(f"/api/v1/payroll/run/{run_id}/approve/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_payroll_run_duplicate_returns_error(self):
        """Duplicate payroll run for same month/year returns validation error."""
        self.client.force_authenticate(user=self.hr_user)
        data = {"payroll_month": 5, "payroll_year": 2026}
        response = self.client.post("/api/v1/payroll/run/", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Attempt duplicate
        response2 = self.client.post("/api/v1/payroll/run/", data)
        self.assertIn(response2.status_code, [status.HTTP_400_BAD_REQUEST, status.HTTP_409_CONFLICT])

    def test_payroll_run_invalid_data(self):
        """Invalid month/year returns 400."""
        self.client.force_authenticate(user=self.hr_user)
        response = self.client.post("/api/v1/payroll/run/", {"payroll_month": 13, "payroll_year": 2026})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ─── Payslip API ────────────────────────────────────────────────────────

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

    def test_payslip_list_as_hr(self):
        """HR can see all payslips."""
        run = PayrollService.create_payroll_run(payroll_month=9, payroll_year=2026, processed_by=self.hr_user)
        self.client.force_authenticate(user=self.hr_user)
        response = self.client.get("/api/v1/payroll/payslips/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_payslip_download_regenerates_if_no_file(self):
        """Payslip download regenerates PDF if file is missing."""
        run = PayrollService.create_payroll_run(payroll_month=2, payroll_year=2027, processed_by=self.hr_user)
        payslip = Payslip.objects.get(payroll_run=run, employee=self.employee)
        # Clear the pdf_path to simulate missing file
        Payslip.objects.filter(id=payslip.id).update(pdf_path=None)
        payslip.refresh_from_db()

        self.client.force_authenticate(user=self.emp_user)
        response = self.client.get(f"/api/v1/payroll/payslips/{payslip.id}/download/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    # ─── Dashboard API ──────────────────────────────────────────────────────

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
        response = self.client.get("/api/v1/payroll/reports/export/", data={"export_format": "csv", "month": 11, "year": 2026})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/csv')

        # Export Excel
        response = self.client.get("/api/v1/payroll/reports/export/", data={"export_format": "excel", "month": 11, "year": 2026})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('spreadsheetml', response['Content-Type'])

        # Export PDF
        response = self.client.get("/api/v1/payroll/reports/export/", data={"export_format": "pdf", "month": 11, "year": 2026})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')

        # Unsupported export format
        response = self.client.get("/api/v1/payroll/reports/export/", data={"export_format": "invalid"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Invalid report type - now routed to catch-all and returns 400
        response = self.client.get("/api/v1/payroll/reports/unknown_type/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_employee_permission_denied_on_reports(self):
        self.client.force_authenticate(user=self.emp_user)

        response = self.client.get("/api/v1/payroll/reports/summary/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.get("/api/v1/payroll/reports/department/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.get("/api/v1/payroll/reports/export/", data={"export_format": "csv"})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_salary_history_without_employee_id_as_employee(self):
        """Employee can view own salary history without specifying employee_id."""
        run = PayrollService.create_payroll_run(payroll_month=3, payroll_year=2027, processed_by=self.hr_user)
        self.client.force_authenticate(user=self.emp_user)
        response = self.client.get("/api/v1/payroll/reports/history/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_salary_history_employee_cannot_view_others(self):
        """Employee cannot view another employee's salary history."""
        other_user = User.objects.create_user(
            username="other_emp", email="other@example.com",
            password="Password123!", role="employee"
        )
        other_employee = Employee.objects.create(
            employee_id="EMP999",
            first_name="Other",
            last_name="Person",
            email="other.person@example.com",
            dob="1990-01-01",
            gender="male",
            designation="Staff",
            salary=Decimal("3000.00"),
            joining_date="2023-01-01",
            user=other_user
        )
        self.client.force_authenticate(user=self.emp_user)
        response = self.client.get(
            "/api/v1/payroll/reports/history/",
            data={"employee_id": other_employee.id}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_salary_history_requires_employee_id_for_user_without_profile(self):
        """User without employee profile must supply employee_id."""
        self.client.force_authenticate(user=self.hr_user)
        response = self.client.get("/api/v1/payroll/reports/history/")
        # HR without employee profile returns 400 (no employee_id)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_export_without_month_year_uses_latest_run(self):
        """Export with no month/year falls back to latest payroll run."""
        PayrollService.create_payroll_run(payroll_month=7, payroll_year=2026, processed_by=self.hr_user)
        self.client.force_authenticate(user=self.hr_user)
        response = self.client.get("/api/v1/payroll/reports/export/", data={"export_format": "csv"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_export_no_run_uses_fallback_month_year(self):
        """Export with no payroll runs falls back to month=1, year=2026."""
        self.client.force_authenticate(user=self.hr_user)
        response = self.client.get("/api/v1/payroll/reports/export/", data={"export_format": "csv"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_access_denied(self):
        """Unauthenticated requests are denied."""
        response = self.client.get("/api/v1/payroll/salary-structure/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = self.client.get("/api/v1/payroll/run/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_month_year_in_reports(self):
        """Reports with invalid month/year return 400."""
        self.client.force_authenticate(user=self.hr_user)
        response = self.client.get("/api/v1/payroll/reports/summary/", data={"month": "abc", "year": "xyz"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_dashboard_not_accessible_by_employee(self):
        """Dashboard endpoint requires PayrollAdmin (admin/hr) role."""
        self.client.force_authenticate(user=self.emp_user)
        response = self.client.get("/api/v1/payroll/dashboard/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ─── Legacy API ─────────────────────────────────────────────────────────

    def test_legacy_payroll_generate(self):
        """Legacy /generate/ endpoint generates payroll for active employees."""
        self.client.force_authenticate(user=self.hr_user)
        response = self.client.post(
            "/api/v1/payroll/generate/",
            data={"month": 8, "year": 2026}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

    def test_legacy_payroll_generate_missing_params(self):
        """Legacy generate without month/year returns 400."""
        self.client.force_authenticate(user=self.hr_user)
        response = self.client.post("/api/v1/payroll/generate/", data={})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_legacy_payroll_generate_invalid_params(self):
        """Legacy generate with invalid month/year returns 400."""
        self.client.force_authenticate(user=self.hr_user)
        response = self.client.post(
            "/api/v1/payroll/generate/",
            data={"month": "abc", "year": "xyz"}
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
