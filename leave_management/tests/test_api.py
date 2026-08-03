import datetime
from decimal import Decimal
from rest_framework import status
from rest_framework.test import APITestCase

from enterprise_hrms.accounts.models import User
from enterprise_hrms.employees.models import Employee
from enterprise_hrms.departments.models import Department
from enterprise_hrms.leave_management.models import LeaveType, LeaveBalance, LeaveRequest


class LeaveApiTests(APITestCase):
    def setUp(self):
        # 1. Users
        self.admin = User.objects.create_user(
            username="admin", email="admin@test.com", password="Password123!", role="admin"
        )
        self.hr = User.objects.create_user(
            username="hr", email="hr@test.com", password="Password123!", role="hr"
        )
        self.mgr_user = User.objects.create_user(
            username="mgr", email="mgr@test.com", password="Password123!", role="employee"
        )
        self.emp_user = User.objects.create_user(
            username="emp", email="emp@test.com", password="Password123!", role="employee"
        )

        # 2. Department & Employees
        self.dept = Department.objects.create(name="Engineering", code="ENG", description="Engineering")

        self.mgr_emp = Employee.objects.create(
            employee_id="M100", first_name="Manager", last_name="Boss", email="mgr@test.com",
            dob="1985-01-01", gender="male", department=self.dept, designation="Lead",
            salary=Decimal("8000.00"), joining_date="2020-01-01", user=self.mgr_user
        )
        self.dept.manager = self.mgr_emp
        self.dept.save()

        self.emp = Employee.objects.create(
            employee_id="E100", first_name="John", last_name="Doe", email="emp@test.com",
            dob="1992-02-02", gender="male", department=self.dept, designation="Developer",
            salary=Decimal("5000.00"), joining_date="2025-01-01", user=self.emp_user
        )

        # 3. Leave Types & Balances
        self.cl_type = LeaveType.objects.create(name="Casual Leave", code="CL", annual_quota=12, is_paid=True)
        self.sl_type = LeaveType.objects.create(name="Sick Leave", code="SL", annual_quota=10, is_paid=True)

        LeaveBalance.objects.create(employee=self.emp, leave_type=self.cl_type, allocated_days=12, used_days=0, remaining_days=12, year=2026)
        LeaveBalance.objects.create(employee=self.emp, leave_type=self.sl_type, allocated_days=10, used_days=0, remaining_days=10, year=2026)

    def test_leave_types_crud(self):
        # List leave types
        self.client.force_authenticate(user=self.emp_user)
        response = self.client.get('/api/v1/leaves/types/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Employee cannot create leave type
        response = self.client.post('/api/v1/leaves/types/', {"name": "Test", "code": "TST", "annual_quota": 5})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # HR can create leave type
        self.client.force_authenticate(user=self.hr)
        response = self.client.post('/api/v1/leaves/types/', {"name": "WFH", "code": "WFH", "annual_quota": 24, "is_paid": True})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_apply_and_my_leaves_and_my_balance(self):
        self.client.force_authenticate(user=self.emp_user)

        # Apply leave
        payload = {
            "leave_type": "CL",
            "start_date": "2026-08-03",
            "end_date": "2026-08-05",
            "reason": "Personal work"
        }
        response = self.client.post('/api/v1/leaves/apply/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        req_id = response.data['data']['id']

        # Get my-leaves
        response = self.client.get('/api/v1/leaves/my-leaves/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Get my-balance
        response = self.client.get('/api/v1/leaves/my-balance/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

    def test_full_approval_workflow_api(self):
        # Employee applies
        self.client.force_authenticate(user=self.emp_user)
        payload = {
            "leave_type": "SL",
            "start_date": "2026-08-10",
            "end_date": "2026-08-11",
            "reason": "Fever"
        }
        response = self.client.post('/api/v1/leaves/apply/', payload, format='json')
        req_id = response.data['data']['id']

        # Manager pending check & approve
        self.client.force_authenticate(user=self.mgr_user)
        pending_resp = self.client.get('/api/v1/leaves/pending/')
        self.assertEqual(pending_resp.status_code, status.HTTP_200_OK)

        app_resp = self.client.put(f'/api/v1/leaves/{req_id}/approve/', {"comments": "Approved"}, format='json')
        self.assertEqual(app_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(app_resp.data['data']['status'], 'pending_hr')

        # HR final approve
        self.client.force_authenticate(user=self.hr)
        hr_resp = self.client.put(f'/api/v1/leaves/{req_id}/final-approve/', {"comments": "HR Approved"}, format='json')
        self.assertEqual(hr_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(hr_resp.data['data']['status'], 'approved')

    def test_cancel_leave_api(self):
        self.client.force_authenticate(user=self.emp_user)
        payload = {
            "leave_type": "CL",
            "start_date": "2026-08-17",
            "end_date": "2026-08-18",
            "reason": "Personal"
        }
        response = self.client.post('/api/v1/leaves/apply/', payload, format='json')
        req_id = response.data['data']['id']

        # Cancel leave
        cancel_resp = self.client.put(f'/api/v1/leaves/{req_id}/cancel/', {"reason": "Not needed"}, format='json')
        self.assertEqual(cancel_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(cancel_resp.data['data']['status'], 'cancelled')

    def test_calendar_analytics_and_report_apis(self):
        self.client.force_authenticate(user=self.hr)

        # Monthly calendar
        res = self.client.get('/api/v1/leaves/calendar/monthly/?month=8&year=2026')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Team calendar
        res = self.client.get('/api/v1/leaves/calendar/team/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Upcoming leaves
        res = self.client.get('/api/v1/leaves/calendar/upcoming/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Currently on leave
        res = self.client.get('/api/v1/leaves/calendar/currently-on-leave/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Analytics
        res = self.client.get('/api/v1/leaves/analytics/?year=2026')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Report PDF export
        res = self.client.get('/api/v1/leaves/report/?report_format=pdf')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res['Content-Type'], 'application/pdf')

        # Report Excel export
        res = self.client.get('/api/v1/leaves/report/?report_format=excel')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Report CSV export
        res = self.client.get('/api/v1/leaves/report/?report_format=csv')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
