import datetime
from django.test import TestCase
from rest_framework.exceptions import ValidationError

from enterprise_hrms.accounts.models import User
from enterprise_hrms.employees.models import Employee
from enterprise_hrms.departments.models import Department
from enterprise_hrms.asset_management.models import (
    AssetCategory, Asset, AssetAssignment, AssetMaintenance,
    SupportTicket, SoftwareLicense,
)
from enterprise_hrms.asset_management.services import (
    create_asset,
    assign_asset,
    return_asset,
    schedule_maintenance,
    create_ticket,
    assign_ticket,
    close_ticket,
    asset_summary,
)
from enterprise_hrms.asset_management.maintenance import (
    complete_maintenance, cancel_maintenance,
)


class ServiceTestBase(TestCase):
    """Shared fixtures for service layer tests."""

    def setUp(self):
        self.dept = Department.objects.create(name="IT", code="ITDEP", description="IT")
        self.admin_user = User.objects.create_user(
            username="admin1", email="admin@hrms.com",
            password="Admin@123", role="admin"
        )
        self.it_user = User.objects.create_user(
            username="it1", email="it@hrms.com",
            password="Pass@123", role="it"
        )
        self.emp_user = User.objects.create_user(
            username="emp1", email="emp@hrms.com",
            password="Pass@123", role="employee"
        )
        self.employee = Employee.objects.create(
            employee_id="EMP-01", first_name="Alice", last_name="Smith",
            email="emp@hrms.com", dob="1992-01-01", gender="female",
            department=self.dept, designation="Dev",
            salary=50000, joining_date="2023-01-01", user=self.emp_user,
        )
        self.it_employee = Employee.objects.create(
            employee_id="IT-01", first_name="Bob", last_name="Jones",
            email="it@hrms.com", dob="1990-06-01", gender="male",
            department=self.dept, designation="IT Engineer",
            salary=60000, joining_date="2022-01-01", user=self.it_user,
        )
        self.category = AssetCategory.objects.create(name="Laptop", code="LAP")
        self.asset = Asset.objects.create(
            asset_code="ASSET-SVC-001",
            name="ThinkPad X1",
            category=self.category,
            status="available",
            purchase_date=datetime.date(2023, 1, 1),
            warranty_expiry_date=datetime.date(2026, 1, 1),
        )


# ─────────────────────────────────────────────
# create_asset
# ─────────────────────────────────────────────

class CreateAssetServiceTest(ServiceTestBase):

    def test_create_asset_success(self):
        asset = create_asset({
            'asset_code': 'ASSET-NEW-001',
            'name': 'New Laptop',
            'status': 'available',
        }, user=self.admin_user)
        self.assertIsNotNone(asset.pk)
        self.assertEqual(asset.asset_code, 'ASSET-NEW-001')

    def test_create_asset_warranty_validation(self):
        with self.assertRaises(ValidationError):
            create_asset({
                'asset_code': 'ASSET-FAIL',
                'name': 'Bad Asset',
                'purchase_date': datetime.date(2024, 1, 1),
                'warranty_expiry_date': datetime.date(2023, 1, 1),
            }, user=self.admin_user)


# ─────────────────────────────────────────────
# assign_asset
# ─────────────────────────────────────────────

class AssignAssetServiceTest(ServiceTestBase):

    def test_assign_asset_success(self):
        assignment = assign_asset(
            asset=self.asset,
            employee=self.employee,
            assigned_by=self.it_employee,
            user=self.admin_user,
        )
        self.assertEqual(assignment.status, 'active')
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.status, 'assigned')

    def test_assign_asset_not_available(self):
        self.asset.status = 'retired'
        self.asset.save()
        with self.assertRaises(ValidationError):
            assign_asset(self.asset, self.employee, user=self.admin_user)

    def test_assign_asset_already_assigned(self):
        assign_asset(self.asset, self.employee, user=self.admin_user)
        emp2 = Employee.objects.create(
            employee_id="EMP-02", first_name="Carol", last_name="Taylor",
            email="carol@hrms.com", dob="1995-01-01", gender="female",
            department=self.dept, designation="Dev",
            salary=45000, joining_date="2023-01-01",
        )
        with self.assertRaises(ValidationError):
            assign_asset(self.asset, emp2, user=self.admin_user)

    def test_assign_asset_under_maintenance_blocked(self):
        self.asset.status = 'under_maintenance'
        self.asset.save()
        with self.assertRaises(ValidationError):
            assign_asset(self.asset, self.employee, user=self.admin_user)


# ─────────────────────────────────────────────
# return_asset
# ─────────────────────────────────────────────

class ReturnAssetServiceTest(ServiceTestBase):

    def setUp(self):
        super().setUp()
        self.assignment = assign_asset(
            self.asset, self.employee,
            user=self.admin_user,
        )

    def test_return_asset_success(self):
        returned = return_asset(self.assignment, user=self.admin_user)
        self.assertEqual(returned.status, 'returned')
        self.assertIsNotNone(returned.actual_return_date)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.status, 'available')

    def test_return_already_returned_raises(self):
        return_asset(self.assignment, user=self.admin_user)
        with self.assertRaises(ValidationError):
            return_asset(self.assignment, user=self.admin_user)


# ─────────────────────────────────────────────
# schedule_maintenance
# ─────────────────────────────────────────────

class ScheduleMaintenanceServiceTest(ServiceTestBase):

    def test_schedule_maintenance_success(self):
        maintenance = schedule_maintenance(
            asset=self.asset,
            scheduled_date=datetime.date(2026, 9, 1),
            user=self.admin_user,
        )
        self.assertEqual(maintenance.status, 'scheduled')
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.status, 'under_maintenance')

    def test_schedule_maintenance_assigned_asset_fails(self):
        assign_asset(self.asset, self.employee, user=self.admin_user)
        with self.assertRaises(ValidationError):
            schedule_maintenance(
                self.asset,
                scheduled_date=datetime.date(2026, 9, 1),
                user=self.admin_user,
            )

    def test_schedule_maintenance_retired_asset_fails(self):
        self.asset.status = 'retired'
        self.asset.save()
        with self.assertRaises(ValidationError):
            schedule_maintenance(
                self.asset,
                scheduled_date=datetime.date(2026, 9, 1),
                user=self.admin_user,
            )


class CompleteCancelMaintenanceTest(ServiceTestBase):

    def setUp(self):
        super().setUp()
        self.maintenance = schedule_maintenance(
            self.asset,
            scheduled_date=datetime.date(2026, 9, 1),
            user=self.admin_user,
        )

    def test_complete_maintenance(self):
        result = complete_maintenance(self.maintenance, user=self.admin_user)
        self.assertEqual(result.status, 'completed')
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.status, 'available')

    def test_complete_already_completed_raises(self):
        complete_maintenance(self.maintenance, user=self.admin_user)
        self.maintenance.refresh_from_db()
        with self.assertRaises(ValidationError):
            complete_maintenance(self.maintenance, user=self.admin_user)

    def test_cancel_maintenance(self):
        result = cancel_maintenance(self.maintenance, user=self.admin_user)
        self.assertEqual(result.status, 'cancelled')
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.status, 'available')


# ─────────────────────────────────────────────
# Ticket lifecycle
# ─────────────────────────────────────────────

class TicketLifecycleServiceTest(ServiceTestBase):

    def test_create_ticket_success(self):
        ticket = create_ticket(
            employee=self.employee,
            subject="My laptop is broken",
            description="Screen cracked",
            priority="high",
            user=self.emp_user,
        )
        self.assertIsNotNone(ticket.pk)
        self.assertEqual(ticket.status, 'open')

    def test_create_critical_ticket_without_engineer_raises(self):
        with self.assertRaises(ValidationError):
            create_ticket(
                employee=self.employee,
                subject="Critical issue",
                description="Data loss",
                priority="critical",
                assigned_engineer=None,
                user=self.emp_user,
            )

    def test_create_critical_ticket_with_engineer_success(self):
        ticket = create_ticket(
            employee=self.employee,
            subject="Critical issue",
            description="Data loss",
            priority="critical",
            assigned_engineer=self.it_employee,
            user=self.emp_user,
        )
        self.assertEqual(ticket.priority, 'critical')
        self.assertEqual(ticket.assigned_engineer, self.it_employee)

    def test_assign_ticket(self):
        ticket = create_ticket(
            employee=self.employee,
            subject="Issue",
            description="Desc",
            user=self.emp_user,
        )
        ticket = assign_ticket(ticket, self.it_employee, user=self.admin_user)
        self.assertEqual(ticket.assigned_engineer, self.it_employee)
        self.assertEqual(ticket.status, 'in_progress')

    def test_close_ticket(self):
        ticket = create_ticket(
            employee=self.employee,
            subject="Issue",
            description="Desc",
            user=self.emp_user,
        )
        ticket = close_ticket(ticket, resolution_notes="Fixed.", user=self.admin_user)
        self.assertEqual(ticket.status, 'closed')
        self.assertIsNotNone(ticket.closed_at)

    def test_close_already_closed_ticket_raises(self):
        ticket = create_ticket(
            employee=self.employee,
            subject="Issue",
            description="Desc",
            user=self.emp_user,
        )
        close_ticket(ticket, user=self.admin_user)
        ticket.refresh_from_db()
        with self.assertRaises(ValidationError):
            close_ticket(ticket, user=self.admin_user)

    def test_assign_closed_ticket_raises(self):
        ticket = create_ticket(
            employee=self.employee,
            subject="Issue",
            description="Desc",
            user=self.emp_user,
        )
        close_ticket(ticket, user=self.admin_user)
        ticket.refresh_from_db()
        with self.assertRaises(ValidationError):
            assign_ticket(ticket, self.it_employee, user=self.admin_user)


# ─────────────────────────────────────────────
# asset_summary
# ─────────────────────────────────────────────

class AssetSummaryServiceTest(ServiceTestBase):

    def test_asset_summary_keys(self):
        summary = asset_summary()
        self.assertIn('total', summary)
        self.assertIn('available', summary)
        self.assertIn('assigned', summary)
        self.assertIn('under_maintenance', summary)
        self.assertIn('retired', summary)

    def test_asset_summary_values(self):
        summary = asset_summary()
        self.assertGreaterEqual(summary['total'], 1)
        self.assertGreaterEqual(summary['available'], 1)
