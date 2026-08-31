import datetime
from django.test import TestCase
from decimal import Decimal

from enterprise_hrms.accounts.models import User
from enterprise_hrms.employees.models import Employee
from enterprise_hrms.leave_management.models import LeaveRequest
from enterprise_hrms.payroll.models import Payroll
from enterprise_hrms.payroll.utils import calculate_unpaid_leave_days, generate_payslip_pdf
from enterprise_hrms.reports.utils import generate_csv_report, generate_excel_report, generate_pdf_report

class ServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password="Password123!"
        )
        self.employee = Employee.objects.create(
            employee_id="EMP001", first_name="John", last_name="Doe", email="test@example.com",
            dob="1990-05-05", gender="male", designation="Developer", salary=Decimal("3000.00"),
            joining_date="2025-01-01", user=self.user
        )

    def test_unpaid_leave_days_calculation(self):
        from enterprise_hrms.leave_management.models import LeaveType
        unpaid_lt = LeaveType.objects.create(name='Unpaid Leave', code='unpaid', annual_quota=30, is_paid=False)

        # 1. No unpaid leaves
        days = calculate_unpaid_leave_days(self.employee, 6, 2026)
        self.assertEqual(days, 0)
        
        # 2. Approved unpaid leave entirely in June (June 5 to June 10 = 6 days)
        LeaveRequest.objects.create(
            employee=self.employee, leave_type=unpaid_lt, status='approved',
            reason="Sick", start_date=datetime.date(2026, 6, 5), end_date=datetime.date(2026, 6, 10), total_days=6
        )
        
        # 3. Approved unpaid leave overlapping June (May 28 to June 3 -> June 1 to June 3 = 3 days)
        LeaveRequest.objects.create(
            employee=self.employee, leave_type=unpaid_lt, status='approved',
            reason="Trip", start_date=datetime.date(2026, 5, 28), end_date=datetime.date(2026, 6, 3), total_days=7
        )
        
        # 4. Rejected unpaid leave (should be ignored)
        LeaveRequest.objects.create(
            employee=self.employee, leave_type=unpaid_lt, status='rejected',
            reason="Trip", start_date=datetime.date(2026, 6, 15), end_date=datetime.date(2026, 6, 18), total_days=4
        )

        total_days = calculate_unpaid_leave_days(self.employee, 6, 2026)
        self.assertEqual(total_days, 9)

    def test_generate_payslip_pdf(self):
        payroll = Payroll.objects.create(
            employee=self.employee, month=6, year=2026,
            basic_salary=Decimal("3000.00"), allowances=Decimal("300.00"),
            deductions=Decimal("100.00"), net_salary=Decimal("3200.00"), status='generated'
        )
        pdf_bytes = generate_payslip_pdf(payroll)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(len(pdf_bytes) > 0)

    def test_reports_exporters(self):
        headers = ['ID', 'Name', 'Role']
        rows = [
            [1, 'Alice', 'Admin'],
            [2, 'Bob', 'Employee']
        ]
        
        # Test CSV
        csv_bytes = generate_csv_report(headers, rows)
        self.assertIsInstance(csv_bytes, bytes)
        self.assertTrue(len(csv_bytes) > 0)
        
        # Test Excel
        excel_bytes = generate_excel_report("Test Report", headers, rows)
        self.assertIsInstance(excel_bytes, bytes)
        self.assertTrue(len(excel_bytes) > 0)
        
        # Test PDF
        pdf_bytes = generate_pdf_report("Test Report", headers, rows)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(len(pdf_bytes) > 0)
