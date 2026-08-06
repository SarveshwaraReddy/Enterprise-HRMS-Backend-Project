import datetime
from django.test import TestCase
from rest_framework.exceptions import ValidationError

from enterprise_hrms.accounts.models import User
from enterprise_hrms.employees.models import Employee
from enterprise_hrms.departments.models import Department
from enterprise_hrms.leave_management.models import LeaveType, LeaveBalance, LeaveRequest
from enterprise_hrms.leave_management.services import (
    apply_leave,
    approve_leave,
    reject_leave,
    final_approve_leave,
    cancel_leave,
    calculate_leave_days,
    get_or_create_leave_balance,
    employee_leave_summary
)


class LeaveServiceTests(TestCase):
    def setUp(self):
        # Admin / Manager / Employee Users
        self.admin_user = User.objects.create_user(
            username="admin_user", email="admin@hrms.com", password="Password123!", role="admin"
        )
        self.hr_user = User.objects.create_user(
            username="hr_user", email="hr@hrms.com", password="Password123!", role="hr"
        )
        self.manager_user = User.objects.create_user(
            username="manager_user", email="mgr@hrms.com", password="Password123!", role="employee"
        )
        self.emp_user = User.objects.create_user(
            username="emp_user", email="emp@hrms.com", password="Password123!", role="employee"
        )

        # Department & Employees
        self.dept = Department.objects.create(name="Engineering", code="ENG", description="Eng")

        self.manager_emp = Employee.objects.create(
            employee_id="M100", first_name="Manager", last_name="Boss", email="mgr@hrms.com",
            dob="1985-01-01", gender="male", department=self.dept, designation="Lead",
            salary=9000, joining_date="2020-01-01", user=self.manager_user
        )
        self.dept.manager = self.manager_emp
        self.dept.save()

        self.emp = Employee.objects.create(
            employee_id="E101", first_name="John", last_name="Doe", email="emp@hrms.com",
            dob="1995-05-05", gender="male", department=self.dept, designation="Developer",
            salary=5000, joining_date="2025-01-01", user=self.emp_user
        )

        self.cl_type = LeaveType.objects.create(name="Casual Leave", code="CL", annual_quota=12, is_paid=True)
        self.sl_type = LeaveType.objects.create(name="Sick Leave", code="SL", annual_quota=10, is_paid=True)

    def test_calculate_leave_days(self):
        # Mon to Fri (5 days)
        start = datetime.date(2026, 8, 3) # Mon
        end = datetime.date(2026, 8, 7) # Fri
        days = calculate_leave_days(start, end, exclude_weekends=True)
        self.assertEqual(days, 5)

        # Mon to Sun (5 business days, 2 weekend days)
        end_sun = datetime.date(2026, 8, 9)
        days_no_wknd = calculate_leave_days(start, end_sun, exclude_weekends=True)
        self.assertEqual(days_no_wknd, 5)

        days_all = calculate_leave_days(start, end_sun, exclude_weekends=False)
        self.assertEqual(days_all, 7)

    def test_apply_leave_success_workflow(self):
        start = datetime.date(2026, 8, 3)
        end = datetime.date(2026, 8, 5) # Mon to Wed = 3 days

        req = apply_leave(
            employee=self.emp,
            leave_type=self.cl_type,
            start_date=start,
            end_date=end,
            reason="Vacation"
        )
        self.assertEqual(req.status, 'pending_manager')
        self.assertEqual(req.total_days, 3)

        # Approve by manager
        req = approve_leave(req, approver_user=self.manager_user, comments="OK by manager")
        self.assertEqual(req.status, 'pending_hr')
        self.assertEqual(req.manager_comments, "OK by manager")

        # Final approve by HR
        req = final_approve_leave(req, hr_user=self.hr_user, comments="Final HR OK")
        self.assertEqual(req.status, 'approved')
        self.assertIsNotNone(req.approved_at)

        # Verify balance deduction
        bal = LeaveBalance.objects.get(employee=self.emp, leave_type=self.cl_type, year=2026)
        self.assertEqual(bal.used_days, 3)
        self.assertEqual(bal.remaining_days, 9)

    def test_apply_leave_validation_errors(self):
        # End date before start date
        with self.assertRaises(ValidationError):
            apply_leave(
                employee=self.emp,
                leave_type=self.cl_type,
                start_date=datetime.date(2026, 8, 5),
                end_date=datetime.date(2026, 8, 1),
                reason="Invalid"
            )

        # Insufficient balance
        small_lt = LeaveType.objects.create(name="Small", code="SML", annual_quota=1, is_paid=True)
        with self.assertRaises(ValidationError):
            apply_leave(
                employee=self.emp,
                leave_type=small_lt,
                start_date=datetime.date(2026, 8, 3),
                end_date=datetime.date(2026, 8, 7), # 5 days vs 1 quota
                reason="Too long"
            )

    def test_overlapping_leave_validation(self):
        start1 = datetime.date(2026, 8, 3)
        end1 = datetime.date(2026, 8, 5)
        apply_leave(self.emp, self.cl_type, start1, end1, "First Leave")

        # Overlapping application
        start2 = datetime.date(2026, 8, 4)
        end2 = datetime.date(2026, 8, 6)
        with self.assertRaises(ValidationError):
            apply_leave(self.emp, self.sl_type, start2, end2, "Overlapping Leave")

    def test_reject_leave_workflow(self):
        start = datetime.date(2026, 8, 3)
        end = datetime.date(2026, 8, 4)
        req = apply_leave(self.emp, self.cl_type, start, end, "Reason")

        req = reject_leave(req, reviewer_user=self.manager_user, comments="Rejected")
        self.assertEqual(req.status, 'rejected')

    def test_cancel_leave_restores_balance(self):
        start = datetime.date(2026, 8, 3)
        end = datetime.date(2026, 8, 4)
        req = apply_leave(self.emp, self.cl_type, start, end, "Trip")
        req = approve_leave(req, self.manager_user)
        req = final_approve_leave(req, self.hr_user)

        bal = LeaveBalance.objects.get(employee=self.emp, leave_type=self.cl_type, year=2026)
        self.assertEqual(bal.used_days, 2)

        # Cancel leave
        req = cancel_leave(req, user=self.emp_user, reason="Plans changed")
        self.assertEqual(req.status, 'cancelled')

        bal.refresh_from_db()
        self.assertEqual(bal.used_days, 0)
        self.assertEqual(bal.remaining_days, 12)

    def test_employee_leave_summary(self):
        get_or_create_leave_balance(self.emp, self.cl_type, 2026)
        summary = employee_leave_summary(self.emp, 2026)
        self.assertEqual(summary['employee_code'], "E101")
        self.assertTrue(len(summary['balances']) >= 2)
