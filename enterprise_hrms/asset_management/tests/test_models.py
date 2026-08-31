import datetime
from django.test import TestCase
from django.db import IntegrityError
from enterprise_hrms.accounts.models import User
from enterprise_hrms.employees.models import Employee
from enterprise_hrms.departments.models import Department
from enterprise_hrms.asset_management.models import (
    AssetCategory, Asset, AssetAssignment, AssetMaintenance,
    SupportTicket, SoftwareLicense,
)


class AssetManagementModelTestBase(TestCase):
    """Shared test fixtures for all asset management model tests."""

    def setUp(self):
        self.dept = Department.objects.create(name="IT", code="IT01", description="IT Dept")
        self.user = User.objects.create_user(
            username="emp_test", email="emp@hrms.com", password="Pass123!", role="employee"
        )
        self.employee = Employee.objects.create(
            employee_id="E001", first_name="John", last_name="Doe",
            email="emp@hrms.com", dob="1990-01-01", gender="male",
            department=self.dept, designation="Engineer",
            salary=50000, joining_date="2023-01-01", user=self.user,
        )
        self.category = AssetCategory.objects.create(name="Laptop", code="LAP")
        self.asset = Asset.objects.create(
            asset_code="ASSET-001", name="Dell XPS 15",
            category=self.category,
            serial_number="SN123",
            vendor="Dell",
            purchase_date=datetime.date(2023, 1, 1),
            warranty_expiry_date=datetime.date(2026, 1, 1),
            status="available",
        )


class AssetCategoryModelTest(AssetManagementModelTestBase):

    def test_category_str(self):
        self.assertEqual(str(self.category), "Laptop (LAP)")

    def test_category_unique_name(self):
        with self.assertRaises(Exception):
            AssetCategory.objects.create(name="Laptop", code="LAP2")

    def test_category_unique_code(self):
        with self.assertRaises(Exception):
            AssetCategory.objects.create(name="Laptop2", code="LAP")

    def test_category_ordering(self):
        AssetCategory.objects.create(name="Mobile", code="MOB")
        cats = list(AssetCategory.objects.values_list('code', flat=True))
        self.assertEqual(cats, sorted(cats))


class AssetModelTest(AssetManagementModelTestBase):

    def test_asset_str(self):
        self.assertIn("ASSET-001", str(self.asset))
        self.assertIn("Dell XPS 15", str(self.asset))
        self.assertIn("Available", str(self.asset))

    def test_asset_code_unique(self):
        with self.assertRaises(Exception):
            Asset.objects.create(
                asset_code="ASSET-001", name="Another Laptop",
                status="available",
            )

    def test_asset_default_status(self):
        a = Asset.objects.create(asset_code="ASSET-002", name="HP Elitebook")
        self.assertEqual(a.status, "available")

    def test_asset_status_choices(self):
        statuses = [c[0] for c in Asset.STATUS_CHOICES]
        self.assertIn("available", statuses)
        self.assertIn("assigned", statuses)
        self.assertIn("under_maintenance", statuses)
        self.assertIn("retired", statuses)


class AssetAssignmentModelTest(AssetManagementModelTestBase):

    def test_assignment_str(self):
        assignment = AssetAssignment.objects.create(
            asset=self.asset, employee=self.employee,
            assigned_date=datetime.date.today(), status='active',
        )
        self.assertIn("ASSET-001", str(assignment))
        self.assertIn("active", str(assignment))

    def test_assignment_default_status_active(self):
        assignment = AssetAssignment.objects.create(
            asset=self.asset, employee=self.employee,
        )
        self.assertEqual(assignment.status, "active")

    def test_assignment_return(self):
        assignment = AssetAssignment.objects.create(
            asset=self.asset, employee=self.employee, status='active',
        )
        assignment.status = 'returned'
        assignment.actual_return_date = datetime.date.today()
        assignment.save()
        self.assertEqual(assignment.status, 'returned')
        self.assertIsNotNone(assignment.actual_return_date)


class AssetMaintenanceModelTest(AssetManagementModelTestBase):

    def test_maintenance_str(self):
        m = AssetMaintenance.objects.create(
            asset=self.asset,
            scheduled_date=datetime.date(2026, 9, 1),
            status='scheduled',
        )
        self.assertIn("ASSET-001", str(m))
        self.assertIn("scheduled", str(m))

    def test_maintenance_default_status(self):
        m = AssetMaintenance.objects.create(
            asset=self.asset,
            scheduled_date=datetime.date.today(),
        )
        self.assertEqual(m.status, 'scheduled')


class SupportTicketModelTest(AssetManagementModelTestBase):

    def test_ticket_auto_ticket_number(self):
        ticket = SupportTicket.objects.create(
            employee=self.employee,
            subject="Laptop broken",
            description="Screen cracked",
            priority="high",
            status="open",
        )
        self.assertIsNotNone(ticket.ticket_number)
        self.assertTrue(ticket.ticket_number.startswith("TKT-"))

    def test_ticket_str(self):
        ticket = SupportTicket.objects.create(
            employee=self.employee,
            subject="Test issue",
            description="Desc",
            priority="medium",
            status="open",
        )
        self.assertIn("TKT-", str(ticket))
        self.assertIn("Medium", str(ticket))

    def test_ticket_unique_ticket_number(self):
        t1 = SupportTicket.objects.create(
            employee=self.employee, subject="T1", description="D1",
        )
        t2 = SupportTicket.objects.create(
            employee=self.employee, subject="T2", description="D2",
        )
        self.assertNotEqual(t1.ticket_number, t2.ticket_number)

    def test_ticket_priority_choices(self):
        choices = [c[0] for c in SupportTicket.PRIORITY_CHOICES]
        self.assertIn("low", choices)
        self.assertIn("medium", choices)
        self.assertIn("high", choices)
        self.assertIn("critical", choices)

    def test_ticket_status_choices(self):
        choices = [c[0] for c in SupportTicket.STATUS_CHOICES]
        self.assertIn("open", choices)
        self.assertIn("in_progress", choices)
        self.assertIn("on_hold", choices)
        self.assertIn("resolved", choices)
        self.assertIn("closed", choices)


class SoftwareLicenseModelTest(AssetManagementModelTestBase):

    def test_license_str(self):
        lic = SoftwareLicense.objects.create(
            software_name="Microsoft Office",
            license_key="XXXX-YYYY-ZZZZ",
            status="active",
        )
        self.assertIn("Microsoft Office", str(lic))
        self.assertIn("Active", str(lic))

    def test_license_key_unique(self):
        SoftwareLicense.objects.create(
            software_name="Office", license_key="KEY-001"
        )
        with self.assertRaises(Exception):
            SoftwareLicense.objects.create(
                software_name="Office2", license_key="KEY-001"
            )

    def test_license_status_choices(self):
        choices = [c[0] for c in SoftwareLicense.STATUS_CHOICES]
        self.assertIn("active", choices)
        self.assertIn("expired", choices)
        self.assertIn("revoked", choices)
