import datetime
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from enterprise_hrms.accounts.models import User
from enterprise_hrms.employees.models import Employee
from enterprise_hrms.departments.models import Department
from enterprise_hrms.attendance.models import Attendance
from enterprise_hrms.leave_management.models import LeaveRequest
from enterprise_hrms.payroll.models import Payroll
from enterprise_hrms.documents.models import Document
from enterprise_hrms.audit_logs.models import AuditLog
from enterprise_hrms.notifications.models import Notification

class ModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="empuser",
            email="emp@example.com",
            password="Password123!"
        )
        
        self.department = Department.objects.create(
            name="Engineering",
            code="ENG",
            description="Software development department"
        )
        
        self.employee = Employee.objects.create(
            employee_id="EMP101",
            first_name="John",
            last_name="Doe",
            email="john@example.com",
            phone="9876543210",
            dob=datetime.date(1990, 5, 10),
            gender="male",
            department=self.department,
            designation="Software Developer",
            salary=5000.00,
            joining_date=datetime.date(2025, 1, 1),
            user=self.user
        )

    def test_employee_uniqueness_constraints(self):
        from django.db import transaction
        # Email unique
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Employee.objects.create(
                    employee_id="EMP102",
                    first_name="Jane",
                    last_name="Doe",
                    email="john@example.com", # Duplicate email
                    dob=datetime.date(1992, 1, 1),
                    gender="female",
                    designation="Manager",
                    salary=6000.00,
                    joining_date=datetime.date(2025, 1, 1)
                )

        # Employee ID unique
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Employee.objects.create(
                    employee_id="EMP101", # Duplicate id
                    first_name="Jane",
                    last_name="Doe",
                    email="jane@example.com",
                    dob=datetime.date(1992, 1, 1),
                    gender="female",
                    designation="Manager",
                    salary=6000.00,
                    joining_date=datetime.date(2025, 1, 1)
                )

    def test_attendance_unique_together(self):
        # Create first attendance
        Attendance.objects.create(
            employee=self.employee,
            date=datetime.date(2026, 7, 20),
            check_in=datetime.time(9, 0, 0),
            status="present"
        )
        
        # Second attendance for same day should crash unique constraint
        with self.assertRaises(IntegrityError):
            Attendance.objects.create(
                employee=self.employee,
                date=datetime.date(2026, 7, 20),
                check_in=datetime.time(10, 0, 0),
                status="present"
            )

    def test_payroll_model_salary_validator(self):
        # Negative basic salary should raise ValidationError
        p = Payroll(
            employee=self.employee,
            month=6,
            year=2026,
            basic_salary=-500.00, # Invalid
            allowances=100.00,
            deductions=0.00,
            net_salary=-400.00,
            status='draft'
        )
        with self.assertRaises(ValidationError):
            p.full_clean()

    def test_audit_log_creation(self):
        log = AuditLog.objects.create(
            user=self.user,
            action="Employee Created",
            description="John Doe profile created",
            ip_address="127.0.0.1"
        )
        self.assertEqual(log.action, "Employee Created")
        self.assertEqual(log.user, self.user)

    def test_notification_creation(self):
        notif = Notification.objects.create(
            recipient=self.user,
            title="Alert",
            message="Check details"
        )
        self.assertEqual(notif.is_read, False)
        self.assertEqual(notif.recipient, self.user)
