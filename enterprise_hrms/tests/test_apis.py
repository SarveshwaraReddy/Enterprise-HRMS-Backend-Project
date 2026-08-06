import datetime
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from decimal import Decimal
from django.core.files.uploadedfile import SimpleUploadedFile

from enterprise_hrms.accounts.models import User
from enterprise_hrms.employees.models import Employee
from enterprise_hrms.departments.models import Department
from enterprise_hrms.attendance.models import Attendance
from enterprise_hrms.leave_management.models import LeaveRequest
from enterprise_hrms.payroll.models import Payroll
from enterprise_hrms.documents.models import Document

class ApiTests(APITestCase):
    def setUp(self):
        # 1. Users
        self.admin = User.objects.create_user(
            username="admin", email="admin@test.com", password="Password123!", role="admin"
        )
        self.hr = User.objects.create_user(
            username="hr", email="hr@test.com", password="Password123!", role="hr"
        )
        self.emp_user = User.objects.create_user(
            username="emp1", email="emp1@test.com", password="Password123!", role="employee"
        )
        self.emp_user_other = User.objects.create_user(
            username="emp2", email="emp2@test.com", password="Password123!", role="employee"
        )
        
        # 2. Departments
        self.dept = Department.objects.create(name="HR Dept", code="HRD", description="HR Department")
        
        # 3. Employees
        self.employee = Employee.objects.create(
            employee_id="E001", first_name="John", last_name="HR", email="emp1@test.com",
            dob="1995-02-02", gender="male", department=self.dept, designation="Recruiter",
            salary=Decimal("4000.00"), joining_date="2025-01-01", user=self.emp_user
        )
        self.employee_other = Employee.objects.create(
            employee_id="E002", first_name="Bob", last_name="Dev", email="emp2@test.com",
            dob="1995-02-02", gender="male", department=self.dept, designation="Dev",
            salary=Decimal("5000.00"), joining_date="2025-01-01", user=self.emp_user_other
        )
        
        # Set HR employee as manager of department
        self.dept.manager = self.employee
        self.dept.save()

    def test_employee_list_view_permissions(self):
        # Admin can view list
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/v1/employees/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        
        # Employee can view list but only sees self
        self.client.force_authenticate(user=self.emp_user_other)
        response = self.client.get('/api/v1/employees/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['data'][0]['employee_id'], "E002")

    def test_department_statistics(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(f'/api/v1/departments/{self.dept.id}/statistics/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_employees'], 2)

    def test_attendance_mark_flow(self):
        self.client.force_authenticate(user=self.emp_user)
        # Check-in
        response = self.client.post('/api/v1/attendance/mark/')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['data']['status'], 'present')
        self.assertIsNotNone(response.data['data']['check_in'])
        
        # Check-out
        response = self.client.post('/api/v1/attendance/mark/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['data']['check_out'])

    def test_leave_workflow(self):
        from enterprise_hrms.leave_management.models import LeaveType, LeaveBalance
        sick_lt = LeaveType.objects.create(name="Sick Leave", code="sick", annual_quota=10, is_paid=True)
        LeaveBalance.objects.create(employee=self.employee_other, leave_type=sick_lt, allocated_days=10, used_days=0, remaining_days=10, year=2026)

        # Apply leave
        self.client.force_authenticate(user=self.emp_user_other)
        leave_data = {
            "leave_type": "sick",
            "reason": "Cold",
            "start_date": "2026-08-03",
            "end_date": "2026-08-05"
        }
        response = self.client.post('/api/v1/leaves/apply/', leave_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        leave_id = response.data['data']['id']
        self.assertEqual(response.data['data']['status'], 'pending_manager')
        
        # Manager approval (HR recruiter is manager of Bob's department)
        self.client.force_authenticate(user=self.emp_user)
        approve_data = {"status": "approve", "comments": "Approved by manager"}
        response = self.client.put(f'/api/v1/leaves/{leave_id}/approve/', approve_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['status'], 'pending_hr')
        
        # HR approval
        self.client.force_authenticate(user=self.hr)
        hr_data = {"status": "approve", "comments": "Final HR approval"}
        response = self.client.put(f'/api/v1/leaves/{leave_id}/final-approve/', hr_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['status'], 'approved')

    def test_payroll_generation_and_payslip(self):
        self.client.force_authenticate(user=self.hr)
        
        # Generate bulk payroll
        gen_data = {"month": 7, "year": 2026}
        response = self.client.post('/api/v1/payroll/generate/', gen_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 2)
        
        payroll_id = response.data['data'][0]['id']
        
        # Download payslip
        response = self.client.get(f'/api/v1/payroll/{payroll_id}/slip/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_document_upload_and_download(self):
        self.client.force_authenticate(user=self.emp_user)
        
        # Upload
        file_data = SimpleUploadedFile("resume.pdf", b"pdf content here", content_type="application/pdf")
        doc_data = {
            "document_type": "resume",
            "file": file_data
        }
        response = self.client.post('/api/v1/documents/', doc_data, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        doc_id = response.data['id']
        
        # Download (secure download)
        response = self.client.get(f'/api/v1/documents/{doc_id}/download/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(b"".join(response.streaming_content), b"pdf content here")
        
        # Delete (should remove file and record)
        response = self.client.delete(f'/api/v1/documents/{doc_id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_dashboard_view(self):
        self.client.force_authenticate(user=self.hr)
        response = self.client.get('/api/v1/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_employees', response.data['data'])

    def test_report_downloads(self):
        self.client.force_authenticate(user=self.hr)
        
        # Test Employee Reports: CSV, Excel, PDF with filters
        for fmt in ['csv', 'excel', 'pdf']:
            response = self.client.get(f'/api/v1/reports/employees/?report_format={fmt}&department_id={self.dept.id}&status=active')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(len(response.content) > 0)
            
        # Test Department Reports: CSV, Excel, PDF
        for fmt in ['csv', 'excel', 'pdf']:
            response = self.client.get(f'/api/v1/reports/departments/?report_format={fmt}')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(len(response.content) > 0)

        # Test Attendance Reports: CSV, Excel, PDF with filters
        for fmt in ['csv', 'excel', 'pdf']:
            response = self.client.get(f'/api/v1/reports/attendance/?report_format={fmt}&start_date=2026-01-01&end_date=2026-12-31&employee_id={self.employee.id}')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(len(response.content) > 0)

        # Test Payroll Reports: CSV, Excel, PDF with filters
        for fmt in ['csv', 'excel', 'pdf']:
            response = self.client.get(f'/api/v1/reports/payroll/?report_format={fmt}&month=7&year=2026')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertTrue(len(response.content) > 0)

    def test_attendance_additional_endpoints(self):
        self.client.force_authenticate(user=self.emp_user)
        # Check-in first to create record
        self.client.post('/api/v1/attendance/mark/')
        
        # List attendance as employee (covers get_queryset)
        response = self.client.get('/api/v1/attendance/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Monthly attendance get
        response = self.client.get('/api/v1/attendance/monthly/?month=7&year=2026')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Monthly attendance invalid month format
        response = self.client.get('/api/v1/attendance/monthly/?month=invalid&year=2026')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Monthly attendance missing parameters
        response = self.client.get('/api/v1/attendance/monthly/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Monthly attendance as HR (with employee_id)
        self.client.force_authenticate(user=self.hr)
        response = self.client.get(f'/api/v1/attendance/monthly/?month=7&year=2026&employee_id={self.employee.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Monthly attendance as HR with missing employee_id
        response = self.client.get('/api/v1/attendance/monthly/?month=7&year=2026')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Monthly attendance as HR with invalid employee_id
        response = self.client.get('/api/v1/attendance/monthly/?month=7&year=2026&employee_id=99999')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthorized_employee_crud(self):
        self.client.force_authenticate(user=self.emp_user)
        
        # Attempt to create employee as regular employee -> 403
        data = {
            "employee_id": "E999", "first_name": "Test", "last_name": "User", "email": "test99@test.com",
            "dob": "1990-01-01", "gender": "male", "designation": "Staff", "salary": 2000, "joining_date": "2026-01-01"
        }
        response = self.client.post('/api/v1/employees/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Attempt to delete employee -> 403
        response = self.client.delete(f'/api/v1/employees/{self.employee.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
