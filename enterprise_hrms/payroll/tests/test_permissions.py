"""
Module 11: Permission tests for all payroll module roles.
Tests HR, Payroll Admin, and Employee permission classes across all endpoints.
"""
from decimal import Decimal
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import MagicMock

from enterprise_hrms.employees.models import Employee
from enterprise_hrms.departments.models import Department
from enterprise_hrms.payroll.models import PayrollRun, Payslip
from enterprise_hrms.payroll.services import PayrollService
from enterprise_hrms.payroll.permissions import (
    IsHR, IsPayrollAdmin, IsEmployee, IsPayslipOwnerOrAdmin
)

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

        self.run = PayrollService.create_payroll_run(
            payroll_month=12, payroll_year=2026, processed_by=self.hr_user
        )
        self.payslip1 = Payslip.objects.get(payroll_run=self.run, employee=self.employee1)
        self.payslip2 = Payslip.objects.get(payroll_run=self.run, employee=self.employee2)

    # ─── Endpoint Access Control ────────────────────────────────────────────

    def test_employee_cannot_create_salary_structure(self):
        self.client.force_authenticate(user=self.emp1_user)
        response = self.client.post(
            "/api/v1/payroll/salary-structure/",
            {"employee": self.employee1.id, "basic_salary": "5000.00"}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_cannot_create_payroll_run(self):
        self.client.force_authenticate(user=self.emp1_user)
        response = self.client.post(
            "/api/v1/payroll/run/",
            {"payroll_month": 1, "payroll_year": 2027}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_cannot_access_other_employee_payslip(self):
        self.client.force_authenticate(user=self.emp1_user)
        # emp1 requesting emp2's payslip — filtered out (404) or forbidden
        response = self.client.get(f"/api/v1/payroll/payslips/{self.payslip2.id}/")
        self.assertIn(response.status_code, [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN])

    def test_hr_and_admin_full_access(self):
        self.client.force_authenticate(user=self.hr_user)
        response = self.client.get("/api/v1/payroll/run/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get("/api/v1/payroll/run/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_employee_can_view_own_payslip(self):
        """Employee can view their own payslip."""
        self.client.force_authenticate(user=self.emp1_user)
        response = self.client.get(f"/api/v1/payroll/payslips/{self.payslip1.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_hr_can_view_any_payslip(self):
        """HR can view any employee's payslip."""
        self.client.force_authenticate(user=self.hr_user)
        response = self.client.get(f"/api/v1/payroll/payslips/{self.payslip1.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.get(f"/api/v1/payroll/payslips/{self.payslip2.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_hr_can_approve_payroll(self):
        """HR can approve a payroll run."""
        self.client.force_authenticate(user=self.hr_user)
        run2 = PayrollService.create_payroll_run(
            payroll_month=1, payroll_year=2027, processed_by=self.hr_user
        )
        response = self.client.put(f"/api/v1/payroll/run/{run2.id}/approve/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'approved')

    def test_admin_can_approve_and_release_payroll(self):
        """Admin (superuser) can approve and release payroll."""
        self.client.force_authenticate(user=self.admin_user)
        run3 = PayrollService.create_payroll_run(
            payroll_month=2, payroll_year=2027, processed_by=self.admin_user
        )
        response = self.client.put(f"/api/v1/payroll/run/{run3.id}/approve/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.put(f"/api/v1/payroll/run/{run3.id}/release/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_employee_cannot_approve_payroll(self):
        """Employee cannot approve a payroll run."""
        self.client.force_authenticate(user=self.emp1_user)
        response = self.client.put(f"/api/v1/payroll/run/{self.run.id}/approve/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_cannot_release_payroll(self):
        """Employee cannot release a payroll run."""
        self.client.force_authenticate(user=self.emp1_user)
        response = self.client.put(f"/api/v1/payroll/run/{self.run.id}/release/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_cannot_delete_salary_structure(self):
        """Employee cannot delete a salary structure."""
        self.client.force_authenticate(user=self.emp1_user)
        struct = PayrollService.create_salary_structure(
            employee_id=self.employee1.id,
            data={"basic_salary": Decimal("4200.00")}
        )
        response = self.client.delete(f"/api/v1/payroll/salary-structure/{struct.id}/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ─── Permission Class Unit Tests ────────────────────────────────────────

    def _make_request(self, user):
        request = MagicMock()
        request.user = user
        return request

    def test_is_hr_permission_class(self):
        perm = IsHR()
        self.assertTrue(perm.has_permission(self._make_request(self.hr_user), None))
        self.assertTrue(perm.has_permission(self._make_request(self.admin_user), None))
        self.assertFalse(perm.has_permission(self._make_request(self.emp1_user), None))

    def test_is_payroll_admin_permission_class(self):
        perm = IsPayrollAdmin()
        self.assertTrue(perm.has_permission(self._make_request(self.hr_user), None))
        self.assertTrue(perm.has_permission(self._make_request(self.admin_user), None))
        self.assertFalse(perm.has_permission(self._make_request(self.emp1_user), None))

    def test_is_employee_permission_class(self):
        perm = IsEmployee()
        self.assertTrue(perm.has_permission(self._make_request(self.emp1_user), None))
        self.assertFalse(perm.has_permission(self._make_request(self.hr_user), None))
        self.assertFalse(perm.has_permission(self._make_request(self.admin_user), None))

    def test_is_payslip_owner_or_admin_permission_class(self):
        perm = IsPayslipOwnerOrAdmin()

        # has_permission always true for authenticated user
        self.assertTrue(perm.has_permission(self._make_request(self.emp1_user), None))

        # has_object_permission: HR can access any
        hr_request = self._make_request(self.hr_user)
        self.assertTrue(perm.has_object_permission(hr_request, None, self.payslip2))

        # has_object_permission: employee can access own
        emp1_request = self._make_request(self.emp1_user)
        self.assertTrue(perm.has_object_permission(emp1_request, None, self.payslip1))

        # has_object_permission: employee cannot access other's
        self.assertFalse(perm.has_object_permission(emp1_request, None, self.payslip2))

    def test_is_payslip_owner_or_admin_no_employee_attr(self):
        """Permission check returns False if obj has no employee attribute."""
        perm = IsPayslipOwnerOrAdmin()
        emp1_request = self._make_request(self.emp1_user)
        obj = MagicMock(spec=[])  # object with no 'employee' attribute
        self.assertFalse(perm.has_object_permission(emp1_request, None, obj))
