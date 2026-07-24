from django.test import TestCase
from django.contrib.auth.models import AnonymousUser
from rest_framework.test import APIRequestFactory
from enterprise_hrms.api.permissions import IsAdmin, IsHR, IsAdminOrHR, IsOwnerOrAdminOrHR
from enterprise_hrms.accounts.models import User
from enterprise_hrms.employees.models import Employee

class PermissionTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.anonymous = AnonymousUser()
        
        self.admin_user = User.objects.create_user(
            username="adminuser", email="admin@example.com", password="Password123!", role="admin"
        )
        self.hr_user = User.objects.create_user(
            username="hruser", email="hr@example.com", password="Password123!", role="hr"
        )
        self.emp_user1 = User.objects.create_user(
            username="emp1", email="emp1@example.com", password="Password123!", role="employee"
        )
        self.emp_user2 = User.objects.create_user(
            username="emp2", email="emp2@example.com", password="Password123!", role="employee"
        )

        self.employee1 = Employee.objects.create(
            employee_id="EMP01", first_name="E1", last_name="L1", email="emp1@example.com",
            dob="1990-01-01", gender="male", designation="Dev", salary=3000, joining_date="2025-01-01",
            user=self.emp_user1
        )
        self.employee2 = Employee.objects.create(
            employee_id="EMP02", first_name="E2", last_name="L2", email="emp2@example.com",
            dob="1990-01-01", gender="male", designation="Dev", salary=3000, joining_date="2025-01-01",
            user=self.emp_user2
        )

    def test_is_admin_permission(self):
        perm = IsAdmin()
        
        req = self.factory.get('/')
        req.user = self.admin_user
        self.assertTrue(perm.has_permission(req, None))
        
        req.user = self.hr_user
        self.assertFalse(perm.has_permission(req, None))
        
        req.user = self.anonymous
        self.assertFalse(perm.has_permission(req, None))

    def test_is_hr_permission(self):
        perm = IsHR()
        
        req = self.factory.get('/')
        req.user = self.hr_user
        self.assertTrue(perm.has_permission(req, None))
        
        req.user = self.admin_user
        self.assertFalse(perm.has_permission(req, None))

    def test_is_admin_or_hr_permission(self):
        perm = IsAdminOrHR()
        
        req = self.factory.get('/')
        req.user = self.admin_user
        self.assertTrue(perm.has_permission(req, None))
        
        req.user = self.hr_user
        self.assertTrue(perm.has_permission(req, None))
        
        req.user = self.emp_user1
        self.assertFalse(perm.has_permission(req, None))

    def test_is_owner_or_admin_or_hr_permission(self):
        perm = IsOwnerOrAdminOrHR()
        
        # Admin request on employee2 profile
        req = self.factory.get('/')
        req.user = self.admin_user
        self.assertTrue(perm.has_object_permission(req, None, self.employee2))
        
        # HR request on employee2 profile
        req.user = self.hr_user
        self.assertTrue(perm.has_object_permission(req, None, self.employee2))
        
        # employee1 request on employee1 profile (Owner)
        req.user = self.emp_user1
        self.assertTrue(perm.has_object_permission(req, None, self.employee1))
        
        # employee1 request on employee2 profile (Not Owner)
        req.user = self.emp_user1
        self.assertFalse(perm.has_object_permission(req, None, self.employee2))
