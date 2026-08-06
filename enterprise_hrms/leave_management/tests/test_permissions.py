from django.test import TestCase
from enterprise_hrms.accounts.models import User
from enterprise_hrms.employees.models import Employee
from enterprise_hrms.departments.models import Department
from enterprise_hrms.leave_management.models import LeaveType, LeaveRequest
from enterprise_hrms.leave_management.permissions import (
    IsLeaveOwnerOrManagerOrHR,
    IsDepartmentManager,
    IsHROrAdmin
)


class MockRequest:
    def __init__(self, user):
        self.user = user


class PermissionTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin_p", email="admin_p@test.com", password="Password123!", role="admin")
        self.hr = User.objects.create_user(username="hr_p", email="hr_p@test.com", password="Password123!", role="hr")
        self.mgr_user = User.objects.create_user(username="mgr_p", email="mgr_p@test.com", password="Password123!", role="employee")
        self.emp1_user = User.objects.create_user(username="emp1_p", email="emp1_p@test.com", password="Password123!", role="employee")
        self.emp2_user = User.objects.create_user(username="emp2_p", email="emp2_p@test.com", password="Password123!", role="employee")

        self.dept = Department.objects.create(name="ENG", code="ENG")
        self.mgr_emp = Employee.objects.create(
            employee_id="M1", first_name="Manager", last_name="User", email="mgr@test.com",
            dob="1980-01-01", gender="male", department=self.dept, designation="Lead", salary=8000,
            joining_date="2025-01-01", user=self.mgr_user
        )
        self.dept.manager = self.mgr_emp
        self.dept.save()

        self.emp1 = Employee.objects.create(
            employee_id="E1", first_name="Emp1", last_name="User", email="emp1@test.com",
            dob="1990-01-01", gender="male", department=self.dept, designation="Dev", salary=5000,
            joining_date="2025-01-01", user=self.emp1_user
        )
        self.emp2 = Employee.objects.create(
            employee_id="E2", first_name="Emp2", last_name="User", email="emp2@test.com",
            dob="1991-01-01", gender="male", designation="Dev", salary=5000,
            joining_date="2025-01-01", user=self.emp2_user
        )

        self.lt = LeaveType.objects.create(name="Casual Leave", code="CL", annual_quota=12)
        self.leave_req = LeaveRequest.objects.create(
            employee=self.emp1, leave_type=self.lt, start_date="2026-08-01", end_date="2026-08-02", total_days=2, reason="Test"
        )

    def test_is_leave_owner_or_manager_or_hr(self):
        perm = IsLeaveOwnerOrManagerOrHR()

        # Admin & HR have permission
        self.assertTrue(perm.has_object_permission(MockRequest(self.admin), None, self.leave_req))
        self.assertTrue(perm.has_object_permission(MockRequest(self.hr), None, self.leave_req))

        # Owner has permission
        self.assertTrue(perm.has_object_permission(MockRequest(self.emp1_user), None, self.leave_req))

        # Manager of department has permission
        self.assertTrue(perm.has_object_permission(MockRequest(self.mgr_user), None, self.leave_req))

        # Unrelated employee has NO permission
        self.assertFalse(perm.has_object_permission(MockRequest(self.emp2_user), None, self.leave_req))

    def test_is_hr_or_admin(self):
        perm = IsHROrAdmin()
        self.assertTrue(perm.has_permission(MockRequest(self.admin), None))
        self.assertTrue(perm.has_permission(MockRequest(self.hr), None))
        self.assertFalse(perm.has_permission(MockRequest(self.emp1_user), None))
