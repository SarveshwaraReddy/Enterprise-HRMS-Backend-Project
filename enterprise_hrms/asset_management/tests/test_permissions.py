import datetime
from django.test import TestCase, RequestFactory
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework import status

from enterprise_hrms.accounts.models import User
from enterprise_hrms.employees.models import Employee
from enterprise_hrms.departments.models import Department
from enterprise_hrms.asset_management.models import (
    AssetCategory, Asset, AssetAssignment, SupportTicket,
)
from enterprise_hrms.asset_management.permissions import (
    IsITTeamOrAdmin,
    IsHROrAdmin,
    IsITOrHROrAdmin,
    IsTicketOwnerOrITOrAdmin,
    IsAssetAssigneeOrITOrAdmin,
)
from enterprise_hrms.asset_management.services import assign_asset, create_ticket


class PermissionTestBase(TestCase):
    """Shared fixture for permission tests."""

    def setUp(self):
        self.factory = APIRequestFactory()
        self.dept = Department.objects.create(name="Ops", code="OPS")

        self.admin_user = User.objects.create_user(
            username="perm_admin", email="perm_admin@hrms.com",
            password="Admin@123", role="admin",
        )
        self.hr_user = User.objects.create_user(
            username="perm_hr", email="perm_hr@hrms.com",
            password="Pass@123", role="hr",
        )
        self.it_user = User.objects.create_user(
            username="perm_it", email="perm_it@hrms.com",
            password="Pass@123", role="it",
        )
        self.emp_user = User.objects.create_user(
            username="perm_emp", email="perm_emp@hrms.com",
            password="Pass@123", role="employee",
        )
        self.emp_user2 = User.objects.create_user(
            username="perm_emp2", email="perm_emp2@hrms.com",
            password="Pass@123", role="employee",
        )

        self.employee = Employee.objects.create(
            employee_id="PERM-EMP-01", first_name="Perm", last_name="Emp",
            email="perm_emp@hrms.com", dob="1990-01-01", gender="male",
            department=self.dept, designation="Dev",
            salary=40000, joining_date="2023-01-01", user=self.emp_user,
        )
        self.employee2 = Employee.objects.create(
            employee_id="PERM-EMP-02", first_name="Other", last_name="Emp",
            email="perm_emp2@hrms.com", dob="1992-01-01", gender="female",
            department=self.dept, designation="Analyst",
            salary=45000, joining_date="2023-01-01", user=self.emp_user2,
        )

        self.category = AssetCategory.objects.create(name="Camera", code="CAM")
        self.asset = Asset.objects.create(
            asset_code="PERM-ASSET-001", name="Sony Camera",
            category=self.category, status="available",
        )

    def _make_request(self, user):
        request = self.factory.get('/')
        request.user = user
        return request


# ─────────────────────────────────────────────
# IsITTeamOrAdmin
# ─────────────────────────────────────────────

class IsITTeamOrAdminTest(PermissionTestBase):

    def _check(self, user, expected):
        perm = IsITTeamOrAdmin()
        request = self._make_request(user)
        self.assertEqual(perm.has_permission(request, None), expected)

    def test_admin_allowed(self):
        self._check(self.admin_user, True)

    def test_it_allowed(self):
        self._check(self.it_user, True)

    def test_hr_denied(self):
        self._check(self.hr_user, False)

    def test_employee_denied(self):
        self._check(self.emp_user, False)


# ─────────────────────────────────────────────
# IsHROrAdmin
# ─────────────────────────────────────────────

class IsHROrAdminTest(PermissionTestBase):

    def _check(self, user, expected):
        perm = IsHROrAdmin()
        request = self._make_request(user)
        self.assertEqual(perm.has_permission(request, None), expected)

    def test_admin_allowed(self):
        self._check(self.admin_user, True)

    def test_hr_allowed(self):
        self._check(self.hr_user, True)

    def test_it_denied(self):
        self._check(self.it_user, False)

    def test_employee_denied(self):
        self._check(self.emp_user, False)


# ─────────────────────────────────────────────
# IsITOrHROrAdmin
# ─────────────────────────────────────────────

class IsITOrHROrAdminTest(PermissionTestBase):

    def _check(self, user, expected):
        perm = IsITOrHROrAdmin()
        request = self._make_request(user)
        self.assertEqual(perm.has_permission(request, None), expected)

    def test_admin_allowed(self):
        self._check(self.admin_user, True)

    def test_hr_allowed(self):
        self._check(self.hr_user, True)

    def test_it_allowed(self):
        self._check(self.it_user, True)

    def test_employee_denied(self):
        self._check(self.emp_user, False)


# ─────────────────────────────────────────────
# IsTicketOwnerOrITOrAdmin
# ─────────────────────────────────────────────

class IsTicketOwnerOrITOrAdminTest(PermissionTestBase):

    def setUp(self):
        super().setUp()
        self.ticket = create_ticket(
            employee=self.employee,
            subject="Perm test ticket",
            description="Desc",
            user=self.emp_user,
        )

    def _check_object(self, user, expected):
        perm = IsTicketOwnerOrITOrAdmin()
        request = self._make_request(user)
        self.assertEqual(perm.has_object_permission(request, None, self.ticket), expected)

    def test_admin_has_object_access(self):
        self._check_object(self.admin_user, True)

    def test_it_has_object_access(self):
        self._check_object(self.it_user, True)

    def test_ticket_owner_has_object_access(self):
        self._check_object(self.emp_user, True)

    def test_other_employee_denied_object(self):
        self._check_object(self.emp_user2, False)

    def test_hr_denied_object(self):
        # HR is not IT or admin
        self._check_object(self.hr_user, False)


# ─────────────────────────────────────────────
# IsAssetAssigneeOrITOrAdmin
# ─────────────────────────────────────────────

class IsAssetAssigneeOrITOrAdminTest(PermissionTestBase):

    def setUp(self):
        super().setUp()
        self.assignment = assign_asset(
            self.asset, self.employee, user=self.admin_user,
        )

    def _check_object(self, user, expected):
        perm = IsAssetAssigneeOrITOrAdmin()
        request = self._make_request(user)
        self.assertEqual(perm.has_object_permission(request, None, self.assignment), expected)

    def test_admin_has_object_access(self):
        self._check_object(self.admin_user, True)

    def test_it_has_object_access(self):
        self._check_object(self.it_user, True)

    def test_assignee_has_object_access(self):
        self._check_object(self.emp_user, True)

    def test_non_assignee_denied(self):
        self._check_object(self.emp_user2, False)

    def test_hr_denied(self):
        self._check_object(self.hr_user, False)


# ─────────────────────────────────────────────
# End-to-end permission tests via API
# ─────────────────────────────────────────────

class RoleBasedAPIAccessTest(PermissionTestBase):

    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_admin_can_delete_asset(self):
        asset = Asset.objects.create(asset_code='DEL-PERM-001', name='ToDelete', status='available')
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(f'/api/v1/assets/{asset.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_hr_cannot_delete_asset(self):
        self.client.force_authenticate(user=self.hr_user)
        response = self.client.delete(f'/api/v1/assets/{self.asset.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_employee_cannot_create_asset(self):
        self.client.force_authenticate(user=self.emp_user)
        response = self.client.post('/api/v1/assets/', {
            'asset_code': 'EMP-NEW-001', 'name': 'Attempted Asset', 'status': 'available',
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_it_can_close_ticket(self):
        ticket = create_ticket(self.employee, "Perm Close Test", "Desc", user=self.emp_user)
        self.client.force_authenticate(user=self.it_user)
        response = self.client.put(
            f'/api/v1/assets/support/tickets/{ticket.id}/close/',
            {'resolution_notes': 'Done by IT.'},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_employee_cannot_close_own_ticket(self):
        ticket = create_ticket(self.employee, "Self Close Test", "Desc", user=self.emp_user)
        self.client.force_authenticate(user=self.emp_user)
        response = self.client.put(
            f'/api/v1/assets/support/tickets/{ticket.id}/close/',
            {'resolution_notes': 'Self closed.'},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_cannot_list_assets(self):
        response = self.client.get('/api/v1/assets/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
