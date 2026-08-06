import datetime
from decimal import Decimal
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework.exceptions import ValidationError

from enterprise_hrms.accounts.models import User
from enterprise_hrms.employees.models import Employee
from enterprise_hrms.departments.models import Department
from enterprise_hrms.leave_management.models import LeaveType, LeaveBalance, LeaveRequest
from enterprise_hrms.leave_management.validators import (
    validate_leave_dates,
    validate_overlapping_leave,
    validate_leave_balance
)
from enterprise_hrms.leave_management.services import (
    apply_leave,
    approve_leave,
    reject_leave,
    final_approve_leave,
    cancel_leave,
    update_leave_balance,
    calculate_leave_days
)


class AdditionalCoverageTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(username="admin_c", email="admin_c@test.com", password="Password123!", role="admin")
        self.hr = User.objects.create_user(username="hr_c", email="hr_c@test.com", password="Password123!", role="hr")
        self.mgr_user = User.objects.create_user(username="mgr_c", email="mgr_c@test.com", password="Password123!", role="employee")
        self.emp_user = User.objects.create_user(username="emp_c", email="emp_c@test.com", password="Password123!", role="employee")

        self.dept = Department.objects.create(name="Finance", code="FIN", description="Finance Dept")
        self.mgr_emp = Employee.objects.create(
            employee_id="FM100", first_name="Finance", last_name="Mgr", email="mgr_c@test.com",
            dob="1980-01-01", gender="male", department=self.dept, designation="Finance Head",
            salary=Decimal("9000.00"), joining_date="2020-01-01", user=self.mgr_user
        )
        self.dept.manager = self.mgr_emp
        self.dept.save()

        self.emp = Employee.objects.create(
            employee_id="FE100", first_name="Frank", last_name="Finance", email="emp_c@test.com",
            dob="1990-01-01", gender="male", department=self.dept, designation="Accountant",
            salary=Decimal("5000.00"), joining_date="2025-01-01", user=self.emp_user
        )

        self.cl = LeaveType.objects.create(name="Casual Leave", code="CL", annual_quota=12, is_paid=True)
        self.sl = LeaveType.objects.create(name="Sick Leave", code="SL", annual_quota=10, is_paid=True)

    def test_validators_coverage(self):
        # Missing dates
        with self.assertRaises(ValidationError):
            validate_leave_dates(None, datetime.date.today())

        # Past start date without HR override
        yesterday = datetime.date.today() - datetime.timedelta(days=2)
        with self.assertRaises(ValidationError):
            validate_leave_dates(yesterday, datetime.date.today(), is_hr_override=False)

        # Past start date WITH HR override (should pass)
        validate_leave_dates(yesterday, datetime.date.today(), is_hr_override=True)

        # validate_leave_balance without existing balance row
        validate_leave_balance(self.emp, self.cl, total_days=5)

        # validate_leave_balance exceeding quota without balance row
        with self.assertRaises(ValidationError):
            validate_leave_balance(self.emp, self.cl, total_days=15)

    def test_service_additional_branches(self):
        # apply_leave without department manager -> pending_hr
        emp_no_mgr = Employee.objects.create(
            employee_id="NM100", first_name="No", last_name="Manager", email="nomanager@test.com",
            dob="1990-01-01", gender="female", designation="Worker", salary=4000,
            joining_date="2025-01-01", user=User.objects.create_user(username="nomgr", email="nomgr@test.com", password="Password123!")
        )
        req = apply_leave(emp_no_mgr, self.cl, datetime.date(2026, 8, 3), datetime.date(2026, 8, 4), "Personal")
        self.assertEqual(req.status, 'pending_hr')

        # reject_leave by HR user at pending_hr status
        req = approve_leave(apply_leave(self.emp, self.cl, datetime.date(2026, 8, 10), datetime.date(2026, 8, 11), "Vacation"), self.mgr_user)
        self.assertEqual(req.status, 'pending_hr')
        req = reject_leave(req, reviewer_user=self.hr, comments="Denied by HR")
        self.assertEqual(req.status, 'rejected')
        self.assertEqual(req.hr_comments, "Denied by HR")

        # update_leave_balance
        bal = update_leave_balance(self.emp, self.cl, year=2026, allocated_days=15, used_days=2)
        self.assertEqual(bal.allocated_days, 15)
        self.assertEqual(bal.used_days, 2)
        self.assertEqual(bal.remaining_days, 13)

        # calculate_leave_days with start_date > end_date
        self.assertEqual(calculate_leave_days(datetime.date(2026, 8, 5), datetime.date(2026, 8, 1)), 0)

    def test_filters_and_views_coverage(self):
        self.client.force_authenticate(user=self.admin)

        # Create leave request
        req = apply_leave(self.emp, self.cl, datetime.date(2026, 8, 3), datetime.date(2026, 8, 5), "Trip")

        # Filter by employee code
        res = self.client.get('/api/v1/leaves/?employee=FE100')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Filter by department code
        res = self.client.get('/api/v1/leaves/?department=FIN')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Filter by leave type code
        res = self.client.get('/api/v1/leaves/?leave_type=CL')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Filter by manager code
        res = self.client.get('/api/v1/leaves/?manager=FM100')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Filter by year
        res = self.client.get('/api/v1/leaves/?year=2026')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Test reports export: dept_summary excel and csv
        res = self.client.get('/api/v1/leaves/report/?report_format=excel&report_type=dept_summary')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        res = self.client.get('/api/v1/leaves/report/?report_format=csv')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
