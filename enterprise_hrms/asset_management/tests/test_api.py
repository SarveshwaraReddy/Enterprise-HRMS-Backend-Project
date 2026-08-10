import datetime
import json
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from enterprise_hrms.accounts.models import User
from enterprise_hrms.employees.models import Employee
from enterprise_hrms.departments.models import Department
from enterprise_hrms.asset_management.models import (
    AssetCategory, Asset, AssetAssignment, AssetMaintenance,
    SupportTicket, SoftwareLicense,
)
from enterprise_hrms.asset_management.services import assign_asset, create_ticket


class APITestBase(TestCase):
    """Shared setup for all API tests."""

    def setUp(self):
        self.client = APIClient()
        self.dept = Department.objects.create(name="Engineering", code="ENG", description="Eng Dept")

        # Admin user
        self.admin_user = User.objects.create_user(
            username="admin_api", email="admin_api@hrms.com",
            password="Admin@123", role="admin", is_staff=True,
        )
        # IT user
        self.it_user = User.objects.create_user(
            username="it_api", email="it_api@hrms.com",
            password="Pass@123", role="it",
        )
        # Employee user
        self.emp_user = User.objects.create_user(
            username="emp_api", email="emp_api@hrms.com",
            password="Pass@123", role="employee",
        )

        self.employee = Employee.objects.create(
            employee_id="E-API-01", first_name="Jane", last_name="Doe",
            email="emp_api@hrms.com", dob="1995-03-15", gender="female",
            department=self.dept, designation="Developer",
            salary=55000, joining_date="2023-06-01", user=self.emp_user,
        )
        self.it_employee = Employee.objects.create(
            employee_id="IT-API-01", first_name="Mike", last_name="Ross",
            email="it_api@hrms.com", dob="1988-09-01", gender="male",
            department=self.dept, designation="IT Lead",
            salary=70000, joining_date="2021-01-01", user=self.it_user,
        )

        self.category = AssetCategory.objects.create(name="Desktop", code="DSK")
        self.asset = Asset.objects.create(
            asset_code="API-ASSET-001", name="HP Desktop",
            category=self.category, status="available",
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)


# ─────────────────────────────────────────────
# Asset Category API
# ─────────────────────────────────────────────

class AssetCategoryAPITest(APITestBase):

    def test_list_categories_authenticated(self):
        self.authenticate(self.emp_user)
        response = self.client.get('/api/v1/assets/categories/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_category_as_admin(self):
        self.authenticate(self.admin_user)
        data = {'name': 'Mobile Phone', 'code': 'MOB', 'description': 'Smartphones'}
        response = self.client.post('/api/v1/assets/categories/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['code'], 'MOB')

    def test_create_category_as_employee_denied(self):
        self.authenticate(self.emp_user)
        data = {'name': 'Tablet', 'code': 'TAB'}
        response = self.client.post('/api/v1/assets/categories/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_category_unauthenticated(self):
        response = self.client.post('/api/v1/assets/categories/', {'name': 'X', 'code': 'X'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


# ─────────────────────────────────────────────
# Asset CRUD API
# ─────────────────────────────────────────────

class AssetCRUDAPITest(APITestBase):

    def test_list_assets(self):
        self.authenticate(self.emp_user)
        response = self.client.get('/api/v1/assets/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_asset_as_admin(self):
        self.authenticate(self.admin_user)
        data = {
            'asset_code': 'API-ASSET-NEW',
            'name': 'New Monitor',
            'category': self.category.id,
            'status': 'available',
        }
        response = self.client.post('/api/v1/assets/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['asset_code'], 'API-ASSET-NEW')

    def test_create_asset_warranty_validation(self):
        self.authenticate(self.admin_user)
        data = {
            'asset_code': 'BAD-ASSET',
            'name': 'Bad Asset',
            'purchase_date': '2024-01-01',
            'warranty_expiry_date': '2023-01-01',  # before purchase date
        }
        response = self.client.post('/api/v1/assets/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_asset_detail(self):
        self.authenticate(self.emp_user)
        response = self.client.get(f'/api/v1/assets/{self.asset.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['asset_code'], 'API-ASSET-001')

    def test_update_asset_as_admin(self):
        self.authenticate(self.admin_user)
        response = self.client.patch(
            f'/api/v1/assets/{self.asset.id}/',
            {'location': 'Floor 2'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['location'], 'Floor 2')

    def test_delete_asset_as_admin(self):
        self.authenticate(self.admin_user)
        asset2 = Asset.objects.create(asset_code='DEL-001', name='To Delete', status='available')
        response = self.client.delete(f'/api/v1/assets/{asset2.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_delete_asset_as_employee_denied(self):
        self.authenticate(self.emp_user)
        response = self.client.delete(f'/api/v1/assets/{self.asset.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ─────────────────────────────────────────────
# Assignment APIs
# ─────────────────────────────────────────────

class AssetAssignmentAPITest(APITestBase):

    def test_assign_asset_success(self):
        self.authenticate(self.admin_user)
        data = {
            'asset': self.asset.id,
            'employee': self.employee.id,
            'assigned_date': str(datetime.date.today()),
        }
        response = self.client.post('/api/v1/assets/assign/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.status, 'assigned')

    def test_assign_asset_already_assigned(self):
        assign_asset(self.asset, self.employee, user=self.admin_user)
        self.authenticate(self.admin_user)
        data = {
            'asset': self.asset.id,
            'employee': self.employee.id,
        }
        response = self.client.post('/api/v1/assets/assign/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_assign_asset_by_employee_denied(self):
        self.authenticate(self.emp_user)
        data = {'asset': self.asset.id, 'employee': self.employee.id}
        response = self.client.post('/api/v1/assets/assign/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_return_asset_success(self):
        assignment = assign_asset(self.asset, self.employee, user=self.admin_user)
        self.authenticate(self.admin_user)
        response = self.client.put('/api/v1/assets/return/', {'assignment_id': assignment.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.asset.refresh_from_db()
        self.assertEqual(self.asset.status, 'available')

    def test_return_asset_invalid_id(self):
        self.authenticate(self.admin_user)
        response = self.client.put('/api/v1/assets/return/', {'assignment_id': 99999})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_my_assets_employee(self):
        assign_asset(self.asset, self.employee, user=self.admin_user)
        self.authenticate(self.emp_user)
        response = self.client.get('/api/v1/assets/my-assets/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_asset_summary(self):
        self.authenticate(self.admin_user)
        response = self.client.get('/api/v1/assets/summary/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total', response.data)
        self.assertIn('available', response.data)


# ─────────────────────────────────────────────
# IT Support Ticket APIs
# ─────────────────────────────────────────────

class SupportTicketAPITest(APITestBase):

    def test_create_ticket_as_employee(self):
        self.authenticate(self.emp_user)
        data = {
            'employee': self.employee.id,
            'subject': 'My laptop is slow',
            'description': 'Takes 10 mins to boot',
            'priority': 'medium',
            'category': 'hardware',
        }
        response = self.client.post('/api/v1/assets/support/tickets/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('ticket_number', response.data)

    def test_create_critical_ticket_without_engineer(self):
        self.authenticate(self.emp_user)
        data = {
            'employee': self.employee.id,
            'subject': 'Critical issue',
            'description': 'Data loss',
            'priority': 'critical',
            'category': 'software',
        }
        response = self.client.post('/api/v1/assets/support/tickets/', data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_tickets_as_admin(self):
        self.authenticate(self.admin_user)
        response = self.client.get('/api/v1/assets/support/tickets/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_tickets_employee_sees_own_only(self):
        create_ticket(self.employee, "My issue", "Desc", user=self.emp_user)
        # create a ticket for another employee (no user attached – admin creates it)
        other_emp = Employee.objects.create(
            employee_id="OTH-01", first_name="X", last_name="Y",
            email="other@hrms.com", dob="1990-01-01", gender="male",
            department=self.dept, designation="Dev",
            salary=40000, joining_date="2023-01-01",
        )
        # Pass admin_user which has no employee_profile; service handles it gracefully
        create_ticket(other_emp, "Other issue", "Desc", user=self.admin_user)

        self.authenticate(self.emp_user)
        response = self.client.get('/api/v1/assets/support/tickets/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Handle CustomPagination format: {'success': ..., 'data': [...]} or plain list
        data = response.data
        if isinstance(data, dict):
            items = data.get('data', data.get('results', []))
        else:
            items = list(data)

        # Employee should only see their own tickets
        self.assertGreater(len(items), 0)
        for item in items:
            self.assertEqual(item['employee'], self.employee.id)

    def test_close_ticket_as_it(self):
        ticket = create_ticket(
            self.employee, "My issue", "Desc", user=self.emp_user
        )
        self.authenticate(self.it_user)
        response = self.client.put(
            f'/api/v1/assets/support/tickets/{ticket.id}/close/',
            {'resolution_notes': 'Problem fixed.'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'closed')

    def test_close_ticket_as_employee_denied(self):
        ticket = create_ticket(
            self.employee, "My issue", "Desc", user=self.emp_user
        )
        self.authenticate(self.emp_user)
        response = self.client.put(
            f'/api/v1/assets/support/tickets/{ticket.id}/close/',
            {'resolution_notes': 'I fixed it myself.'},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_edit_closed_ticket_fails(self):
        ticket = create_ticket(
            self.employee, "My issue", "Desc", user=self.emp_user
        )
        from enterprise_hrms.asset_management.services import close_ticket
        close_ticket(ticket, user=self.admin_user)
        ticket.refresh_from_db()

        self.authenticate(self.admin_user)
        response = self.client.patch(
            f'/api/v1/assets/support/tickets/{ticket.id}/',
            {'subject': 'Changed Subject'},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_assign_ticket_to_engineer(self):
        ticket = create_ticket(
            self.employee, "Issue", "Desc", user=self.emp_user
        )
        self.authenticate(self.admin_user)
        response = self.client.put(
            f'/api/v1/assets/support/tickets/{ticket.id}/assign/',
            {'engineer': self.it_employee.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['assigned_engineer'], self.it_employee.id)
        self.assertEqual(response.data['status'], 'in_progress')

    def test_update_ticket_put(self):
        ticket = create_ticket(
            self.employee, "Old Subject", "Desc", user=self.emp_user
        )
        self.authenticate(self.admin_user)
        data = {
            'employee': self.employee.id,
            'subject': 'Updated Subject',
            'description': 'Updated description',
            'priority': 'high',
            'category': 'hardware',
            'status': 'in_progress',
        }
        response = self.client.put(
            f'/api/v1/assets/support/tickets/{ticket.id}/', data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['subject'], 'Updated Subject')


# ─────────────────────────────────────────────
# Dashboard API
# ─────────────────────────────────────────────

class DashboardAPITest(APITestBase):

    def test_dashboard_returns_keys(self):
        self.authenticate(self.admin_user)
        response = self.client.get('/api/v1/assets/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('assets', response.data)
        self.assertIn('support_tickets', response.data)
        self.assertIn('maintenance_requests', response.data)
        self.assertIn('expiring_licenses_next_30_days', response.data)

    def test_dashboard_employee_denied(self):
        self.authenticate(self.emp_user)
        response = self.client.get('/api/v1/assets/dashboard/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


# ─────────────────────────────────────────────
# Software License APIs
# ─────────────────────────────────────────────

class SoftwareLicenseAPITest(APITestBase):

    def setUp(self):
        super().setUp()
        self.license = SoftwareLicense.objects.create(
            software_name="AutoCAD",
            license_key="ACA-001-XYZ",
            vendor="Autodesk",
            status="active",
        )

    def test_list_licenses(self):
        self.authenticate(self.emp_user)
        response = self.client.get('/api/v1/assets/licenses/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_license_as_admin(self):
        self.authenticate(self.admin_user)
        data = {
            'software_name': 'Adobe Photoshop',
            'license_key': 'PS-KEY-001',
            'vendor': 'Adobe',
            'license_type': 'subscription',
            'status': 'active',
        }
        response = self.client.post('/api/v1/assets/licenses/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_assign_license_to_employee(self):
        self.authenticate(self.admin_user)
        response = self.client.put(
            f'/api/v1/assets/licenses/{self.license.id}/assign/',
            {'employee': self.employee.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['assigned_employee'], self.employee.id)

    def test_revoke_license(self):
        self.license.assigned_employee = self.employee
        self.license.save()
        self.authenticate(self.admin_user)
        response = self.client.put(f'/api/v1/assets/licenses/{self.license.id}/revoke/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'revoked')
        self.assertIsNone(response.data['assigned_employee'])

    def test_expiring_soon(self):
        self.authenticate(self.admin_user)
        SoftwareLicense.objects.create(
            software_name="Expiring Soon",
            license_key="EXP-001",
            status="active",
            expiry_date=datetime.date.today() + datetime.timedelta(days=10),
        )
        response = self.client.get('/api/v1/assets/licenses/expiring-soon/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)
