import datetime
from django.test import TestCase
from django.db import IntegrityError
from enterprise_hrms.accounts.models import User
from enterprise_hrms.employees.models import Employee
from enterprise_hrms.departments.models import Department
from enterprise_hrms.leave_management.models import LeaveType, LeaveBalance, LeaveRequest


class LeaveManagementModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="emp1", email="emp1@hrms.com", password="Password123!", role="employee"
        )
        self.dept = Department.objects.create(name="Engineering", code="ENG", description="Software Eng")
        self.employee = Employee.objects.create(
            employee_id="E100", first_name="Alice", last_name="Smith", email="emp1@hrms.com",
            dob="1992-04-10", gender="female", department=self.dept, designation="Engineer",
            salary=6000, joining_date="2025-01-01", user=self.user
        )
        self.leave_type = LeaveType.objects.create(
            name="Casual Leave", code="CL", annual_quota=12, is_paid=True
        )

    def test_leave_type_creation_and_str(self):
        self.assertEqual(str(self.leave_type), "Casual Leave (CL)")
        self.assertEqual(self.leave_type.annual_quota, 12)
        self.assertTrue(self.leave_type.is_paid)

    def test_leave_balance_auto_remaining_days(self):
        balance = LeaveBalance.objects.create(
            employee=self.employee,
            leave_type=self.leave_type,
            allocated_days=12,
            used_days=3,
            year=2026
        )
        self.assertEqual(balance.remaining_days, 9)
        self.assertIn("CL (2026): 9/12 remaining", str(balance))

    def test_leave_balance_uniqueness(self):
        LeaveBalance.objects.create(
            employee=self.employee,
            leave_type=self.leave_type,
            allocated_days=12,
            year=2026
        )
        with self.assertRaises(IntegrityError):
            LeaveBalance.objects.create(
                employee=self.employee,
                leave_type=self.leave_type,
                allocated_days=12,
                year=2026
            )

    def test_leave_request_creation_and_str(self):
        req = LeaveRequest.objects.create(
            employee=self.employee,
            leave_type=self.leave_type,
            start_date=datetime.date(2026, 8, 1),
            end_date=datetime.date(2026, 8, 3),
            total_days=3,
            reason="Personal work",
            status="pending_manager"
        )
        self.assertEqual(req.status, "pending_manager")
        self.assertIn("CL (pending_manager)", str(req))
