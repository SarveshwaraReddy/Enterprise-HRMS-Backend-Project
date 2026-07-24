from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from enterprise_hrms.accounts.models import User

class AuthTests(APITestCase):
    def setUp(self):
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.logout_url = reverse('logout')
        self.change_password_url = reverse('change_password')
        
        self.user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "phone": "1234567890",
            "role": "employee",
            "password": "Password123!",
            "password_confirm": "Password123!"
        }

    def test_register_user_success(self):
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.filter(email=self.user_data['email']).count(), 1)

    def test_register_password_mismatch(self):
        data = self.user_data.copy()
        data['password_confirm'] = 'DifferentPassword!'
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password_confirm', response.data['errors'])

    def test_login_success(self):
        # Register user first
        self.client.post(self.register_url, self.user_data, format='json')
        
        # Try logging in
        login_data = {
            "email": self.user_data['email'],
            "password": self.user_data['password']
        }
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_login_failure(self):
        login_data = {
            "email": "wrong@example.com",
            "password": "WrongPassword!"
        }
        response = self.client.post(self.login_url, login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_change_password_success(self):
        # Setup user and authenticate
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="OldPassword123!"
        )
        self.client.force_authenticate(user=user)
        
        change_data = {
            "old_password": "OldPassword123!",
            "new_password": "NewPassword123!",
            "new_password_confirm": "NewPassword123!"
        }
        response = self.client.put(self.change_password_url, change_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(user.check_password("NewPassword123!"))

    def test_logout_success(self):
        user = User.objects.create_user(
            username="logoutuser",
            email="logout@example.com",
            password="Password123!"
        )
        self.client.force_authenticate(user=user)
        
        # Get simplejwt refresh token
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        
        logout_data = {
            "refresh": str(refresh)
        }
        response = self.client.post(self.logout_url, logout_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_205_RESET_CONTENT)
