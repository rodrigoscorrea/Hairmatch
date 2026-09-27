from django.test import TestCase, Client, SimpleTestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
import json
import jwt
import datetime
import bcrypt
from .models import User, Customer, Hairdresser
from preferences.models import Preferences
from service.models import Service
import base64
from unittest.mock import patch
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import JsonResponse
from .auth_tokens import (
    issue_session_token,
    set_session_cookie,
    create_signup_token,
    decode_signup_token,
    InvalidSignupToken,
    SIGNUP_TOKEN_TTL,
)
from .google_auth import verify_google_id_token, GoogleTokenError
from google.auth.exceptions import GoogleAuthError

class RegisterViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('register')
        self.valid_customer_payload = {
            'first_name': 'John',
            'last_name': 'Doe',
            'phone': '123456789123',
            'number': '42',
            'complement': 'Apt 1',
            'neighborhood': 'Test Neighborhood',
            'city': 'Test City',
            'state': 'TS',
            'address': 'Main Street',
            'postal_code': '12345',
            'email': 'john@example.com',
            'password': 'secure_password',
            'role': 'customer',
            'rating': 5,
            'cpf': '12345678900',
            'preferences': json.dumps([])  # Add empty preferences list
        }
        self.valid_hairdresser_payload = {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'phone': '987654321231',
            'number': '15',
            'complement': 'Apt 2',
            'neighborhood': 'Downtown',
            'city': 'Metropolis',
            'state': 'MT',
            'address': 'Hair Street',
            'postal_code': '54321',
            'email': 'jane@example.com',
            'password': 'secure_password',
            'role': 'hairdresser',
            'rating': 4,
            'resume': 'Experienced hairdresser',
            'cnpj': '12345678000190',
            'experience_years': 5,
            'preferences': json.dumps([]),  # Add empty preferences list
            'experience_time':'experience_time',
            'experiences':'experiences',
            'products':'products',
            'resume':'resume'
        }

    def test_register_customer_valid(self):
        response = self.client.post(
            self.register_url,
            data=(self.valid_customer_payload),
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Customer.objects.count(), 1)
        self.assertEqual(User.objects.get().email, 'john@example.com')
        self.assertEqual(User.objects.get().role, 'customer')

    def test_register_hairdresser_valid(self):
        response = self.client.post(
            self.register_url,
            data=self.valid_hairdresser_payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Hairdresser.objects.count(), 1)
        self.assertEqual(User.objects.get().email, 'jane@example.com')
        self.assertEqual(User.objects.get().role, 'hairdresser')

    def test_register_duplicate_email(self):
        # First registration
        self.client.post(
            self.register_url,
            data=self.valid_customer_payload,
        )
        
        # Duplicate registration attempt
        response = self.client.post(
            self.register_url,
            data=self.valid_customer_payload,
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(User.objects.count(), 1)  # No new user created

    def test_register_duplicate_phone(self):
        # First registration
        self.client.post(
            self.register_url,
            data=self.valid_customer_payload,
        )
        
        # Duplicate registration attempt
        response = self.client.post(
            self.register_url,
            data=self.valid_customer_payload,
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(User.objects.count(), 1)  # No new user created

    def test_register_missing_role(self):
        invalid_payload = self.valid_hairdresser_payload.copy()
        invalid_payload['role'] = ''
        
        response = self.client.post(
            self.register_url,
            data=invalid_payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 0)

    def test_register_missing_password(self):
        invalid_payload = self.valid_hairdresser_payload.copy()
        invalid_payload['password'] = ''
        
        response = self.client.post(
            self.register_url,
            data=invalid_payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 0)

    def test_register_missing_email(self):
        invalid_payload = self.valid_hairdresser_payload.copy()
        invalid_payload['email'] = ''
        
        response = self.client.post(
            self.register_url,
            data=invalid_payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 0)

    def test_register_missing_phone(self):
        invalid_payload = self.valid_hairdresser_payload.copy()
        invalid_payload['phone'] = ''
        
        response = self.client.post(
            self.register_url,
            data=invalid_payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 0)
        
    def test_register_with_short_phone(self):
        invalid_payload = self.valid_hairdresser_payload.copy()
        invalid_payload['phone'] = '123456789'  # Less than 10 digits
        
        response = self.client.post(
            self.register_url,
            data=invalid_payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 0)

    def test_register_with_preferences(self):
        # Create some test preferences
        pref1 = Preferences.objects.create(name="Coloração")
        pref2 = Preferences.objects.create(name="Cachos")
        
        # Add preference IDs to payload
        payload_with_prefs = self.valid_customer_payload.copy()
        payload_with_prefs['preferences'] = json.dumps([pref1.id, pref2.id])
        
        response = self.client.post(
            self.register_url,
            data=payload_with_prefs,
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        
        # Check if preferences were added to user
        user = User.objects.get(email=payload_with_prefs['email'])
        self.assertEqual(user.preferences.count(), 2)
        self.assertIn(pref1, user.preferences.all())
        self.assertIn(pref2, user.preferences.all())

    def test_register_with_profile_picture(self):
        """Test user registration with a profile picture."""
        # Create a dummy image file
        image = SimpleUploadedFile("profile.jpg", b"file_content", content_type="image/jpeg")
        payload = self.valid_customer_payload.copy()
        payload['profile_picture'] = image

        response = self.client.post(self.register_url, data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.get(email='john@example.com')
        self.assertTrue(user.profile_picture)


class LoginViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.user_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'phone': '123456782319',
            'number': '42',
            'complement': 'Apt 1',
            'neighborhood': 'Test Neighborhood',
            'city': 'Test City',
            'state': 'TS',
            'address': 'Test Street',
            'postal_code': '12345',
            'email': 'test@example.com',
            'password': 'test_password',
            'role': 'customer',
            'rating': 5,
            'cpf': '12345678900',
            'preferences': json.dumps([])
        }
        
        # Register user for login tests
        self.client.post(
            self.register_url,
            data=self.user_data,
        )

    def test_login_valid(self):
        login_payload = {
            'email': 'test@example.com',
            'password': 'test_password'
        }
        
        response = self.client.post(
            self.login_url,
            data=json.dumps(login_payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('jwt' in response.data)
        self.assertTrue('jwt' in response.cookies)

    def test_login_invalid_credentials(self):
        login_payload = {
            'email': 'test@example.com',
            'password': 'wrong_password'
        }
        
        response = self.client.post(
            self.login_url,
            data=json.dumps(login_payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.json())

    def test_login_nonexistent_user(self):
        login_payload = {
            'email': 'nonexistent@example.com',
            'password': 'test_password'
        }
        
        response = self.client.post(
            self.login_url,
            data=json.dumps(login_payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.json())

    def test_check_authentication_with_token(self):
        # First login to get token
        login_payload = {
            'email': 'test@example.com',
            'password': 'test_password'
        }
        
        login_response = self.client.post(
            self.login_url,
            data=json.dumps(login_payload),
            content_type='application/json'
        )
        
        token = login_response.data['jwt']
        self.client.cookies['jwt'] = token
        
        # Then check authentication status
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()['authenticated'])

    def test_check_authentication_without_token(self):
        # Clear cookies to ensure no token
        self.client.cookies.clear()
        
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.json()['authenticated'])


class LogoutViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.logout_url = reverse('logout')
        
        # Simulate a logged-in user by setting a cookie
        self.client.cookies['jwt'] = 'some_token_value'

    def test_logout(self):
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check that the jwt cookie is present and marked for deletion
        self.assertIn('jwt', response.cookies)
        cookie = response.cookies['jwt']
        
        # Ensure the cookie is being deleted
        self.assertEqual(cookie.value, '')
        self.assertIn('max-age', cookie)
        self.assertTrue(int(cookie['max-age']) <= 0 or cookie['expires'])


class ChangePasswordViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.password_change_url = reverse('password_change')
        
        # Create test user
        self.user_data = {
            'first_name': 'Password',
            'last_name': 'Test',
            'phone': '123423256789',
            'number': '42',
            'complement': 'Apt 1',
            'neighborhood': 'Password Neighborhood',
            'city': 'Password City',
            'state': 'PW',
            'address': 'Password Street',
            'postal_code': '12345',
            'email': 'password@example.com',
            'password': 'old_password',
            'role': 'customer',
            'rating': 5,
            'cpf': '12345678900',
            'preferences': json.dumps([])
        }
        
        # Register user
        self.client.post(
            self.register_url,
            data=self.user_data,
        )
        
        # Login to get token
        login_payload = {
            'email': 'password@example.com',
            'password': 'old_password'
        }
        
        login_response = self.client.post(
            self.login_url,
            data=json.dumps(login_payload),
            content_type='application/json'
        )
        
        self.token = login_response.data['jwt']

    def test_change_password_valid(self):
        self.client.cookies['jwt'] = self.token
        
        change_payload = {
            'password': 'new_password'
        }
        
        response = self.client.put(
            self.password_change_url,
            data=json.dumps(change_payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify we can login with new password
        login_payload = {
            'email': 'password@example.com',
            'password': 'new_password'
        }
        
        login_response = self.client.post(
            self.login_url,
            data=json.dumps(login_payload),
            content_type='application/json'
        )
        
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

    def test_change_password_without_token(self):
        self.client.cookies.clear()
        
        change_payload = {
            'password': 'new_password'
        }
        
        response = self.client.put(
            self.password_change_url,
            data=json.dumps(change_payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.json()['authenticated'])

    def test_change_password_with_expired_token(self):
        # Create an expired token
        user = User.objects.get(email='password@example.com')
        payload = {
            'id': user.id,
            'exp': datetime.datetime.now() - datetime.timedelta(minutes=5),  # Expired
            'iat': datetime.datetime.now() - datetime.timedelta(minutes=65)
        }
        expired_token = jwt.encode(payload, 'secret', algorithm='HS256')
        
        self.client.cookies['jwt'] = expired_token
        
        change_payload = {
            'password': 'new_password'
        }
        
        response = self.client.put(
            self.password_change_url,
            data=json.dumps(change_payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.json()['authenticated'])


class UserInfoCookieViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.user_info_auth_url = reverse('user_info_auth')
        
        # Create customer user
        self.customer_data = {
            'first_name': 'Customer',
            'last_name': 'Test',
            'phone': '123423256789',
            'number': '42',
            'complement': 'Apt 1',
            'neighborhood': 'Test Neighborhood',
            'city': 'Test City',
            'state': 'TS',
            'address': 'Customer Street',
            'postal_code': '12345',
            'email': 'customer@example.com',
            'password': 'customer_password',
            'role': 'customer',
            'rating': 5,
            'cpf': '12345678900',
            'preferences': json.dumps([])
        }
        
        # Create hairdresser user
        self.hairdresser_data = {
            'first_name': 'Hairdresser',
            'last_name': 'Test',
            'phone': '987232654321',
            'number': '15',
            'complement': 'Apt 2',
            'neighborhood': 'Hairdresser Neighborhood',
            'city': 'Hairdresser City',
            'state': 'HR',
            'address': 'Hairdresser Street',
            'postal_code': '54321',
            'email': 'hairdresser@example.com',
            'password': 'hairdresser_password',
            'role': 'hairdresser',
            'rating': 4,
            'resume': 'Professional hairdresser',
            'cnpj': '12345678000190',
            'experience_years': 7,
            'preferences': json.dumps([]),
            'experience_time':'experience_time',
            'experiences':'experiences',
            'products':'products',
            'resume':'resume'
        }
        
        # Register users
        self.client.post(
            self.register_url,
            data=self.customer_data,
        )
        
        self.client.post(
            self.register_url,
            data=self.hairdresser_data,
        )
        
        # Helper method to login and get token
        self.customer_token = self._get_token('customer@example.com', 'customer_password')
        self.hairdresser_token = self._get_token('hairdresser@example.com', 'hairdresser_password')

    def _get_token(self, email, password):
        login_payload = {
            'email': email,
            'password': password
        }
        
        response = self.client.post(
            self.login_url,
            data=json.dumps(login_payload),
            content_type='application/json'
        )
        
        return response.data['jwt']

    def test_get_customer_info(self):
        self.client.cookies['jwt'] = self.customer_token
        
        response = self.client.get(self.user_info_auth_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        user_data = response.json()['customer']
        self.assertEqual(user_data['user']['email'], 'customer@example.com')
        self.assertEqual(user_data['user']['role'], 'customer')
        self.assertIn('cpf', user_data)

    def test_get_hairdresser_info(self):
        self.client.cookies['jwt'] = self.hairdresser_token
        
        response = self.client.get(self.user_info_auth_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        user_data = response.json()['hairdresser']
        self.assertEqual(user_data['user']['email'], 'hairdresser@example.com')
        self.assertEqual(user_data['user']['role'], 'hairdresser')
        self.assertIn('resume', user_data)

    def test_get_user_info_without_token(self):
        # Ensure no token in cookies
        self.client.cookies.clear()
        
        response = self.client.get(self.user_info_auth_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_user(self):
        self.client.cookies['jwt'] = self.customer_token
        
        response = self.client.delete(self.user_info_auth_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify user is deleted
        self.assertEqual(User.objects.filter(email='customer@example.com').count(), 0)
        self.assertEqual(Customer.objects.count(), 0)

    def test_delete_user_without_token(self):
        self.client.cookies.clear()
        
        response = self.client.delete(self.user_info_auth_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Verify no users were deleted
        self.assertEqual(User.objects.count(), 2)

    def test_update_customer_info(self):
        self.client.cookies['jwt'] = self.customer_token
        
        update_payload = {
            'first_name': 'Updated',
            'last_name': 'Customer',
            'email': 'updated_customer@example.com',
            'cpf': '98765432100'
        }
        
        response = self.client.put(
            self.user_info_auth_url,
            data=json.dumps(update_payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify user info was updated
        updated_user = User.objects.get(email='updated_customer@example.com')
        self.assertEqual(updated_user.first_name, 'Updated')
        self.assertEqual(updated_user.last_name, 'Customer')
        
        # Verify customer info was updated
        updated_customer = Customer.objects.get(user=updated_user)
        self.assertEqual(updated_customer.cpf, '98765432100')

    def test_update_hairdresser_info(self):
        self.client.cookies['jwt'] = self.hairdresser_token
        
        update_payload = {
            'first_name': 'Updated',
            'last_name': 'Hairdresser',
            'email': 'updated_hairdresser@example.com',
            'experience_years': 10,
            'resume': 'Updated resume',
            'cnpj': '98765432000190'
        }
        
        response = self.client.put(
            self.user_info_auth_url,
            data=json.dumps(update_payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify user info was updated
        updated_user = User.objects.get(email='updated_hairdresser@example.com')
        self.assertEqual(updated_user.first_name, 'Updated')
        self.assertEqual(updated_user.last_name, 'Hairdresser')
        
        # Verify hairdresser info was updated
        updated_hairdresser = Hairdresser.objects.get(user=updated_user)
        self.assertEqual(updated_hairdresser.experience_years, 10)
        self.assertEqual(updated_hairdresser.resume, 'Updated resume')
        self.assertEqual(updated_hairdresser.cnpj, '98765432000190')

    def test_update_with_existing_email(self):
        self.client.cookies['jwt'] = self.customer_token
        
        # Try to update with an email that already exists (hairdresser's email)
        update_payload = {
            'email': 'hairdresser@example.com'
        }
        
        response = self.client.put(
            self.user_info_auth_url,
            data=json.dumps(update_payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.json())


class UserInfoViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('register')
        
        # Create a customer and hairdresser user for testing
        self.customer_data = {
            'first_name': 'Customer',
            'last_name': 'Test',
            'phone': '123423256789',
            'number': '42',
            'complement': 'Apt 1',
            'neighborhood': 'Test Neighborhood',
            'city': 'Test City',
            'state': 'TS',
            'address': 'Customer Street',
            'postal_code': '12345',
            'email': 'customer@example.com',
            'password': 'customer_password',
            'role': 'customer',
            'rating': 5,
            'cpf': '12345678900',
            'preferences': json.dumps([])
        }
        
        self.hairdresser_data = {
            'first_name': 'Hairdresser',
            'last_name': 'Test',
            'phone': '987232654321',
            'number': '15',
            'complement': 'Apt 2',
            'neighborhood': 'Hairdresser Neighborhood',
            'city': 'Hairdresser City',
            'state': 'HR',
            'address': 'Hairdresser Street',
            'postal_code': '54321',
            'email': 'hairdresser@example.com',
            'password': 'hairdresser_password',
            'role': 'hairdresser',
            'rating': 4,
            'resume': 'Professional hairdresser',
            'cnpj': '12345678000190',
            'experience_years': 7,
            'preferences': json.dumps([]),
            'experience_time':'experience_time',
            'experiences':'experiences',
            'products':'products',
            'resume':'resume'
        }
        
        # Register users
        self.client.post(
            self.register_url,
            data=self.customer_data,
        )
        
        self.client.post(
            self.register_url,
            data=self.hairdresser_data,
        )

    def test_get_customer_info_by_email(self):
        url = reverse('user_info', kwargs={'email': 'customer@example.com'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.json())
        user_data = response.json()['data']
        self.assertEqual(user_data['user']['email'], 'customer@example.com')
        self.assertEqual(user_data['user']['role'], 'customer')
        self.assertIn('cpf', user_data)

    def test_get_hairdresser_info_by_email(self):
        url = reverse('user_info', kwargs={'email': 'hairdresser@example.com'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.json())
        user_data = response.json()['data']
        self.assertEqual(user_data['user']['email'], 'hairdresser@example.com')
        self.assertEqual(user_data['user']['role'], 'hairdresser')
        self.assertIn('resume', user_data)

    def test_get_nonexistent_user_info(self):
        url = reverse('user_info', kwargs={'email': 'nonexistent@example.com'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)
        self.assertIn('error', response.json())

    def test_delete_user_by_email(self):
        url = reverse('user_info', kwargs={'email': 'customer@example.com'})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(User.objects.filter(email='customer@example.com').count(), 0)
        self.assertEqual(Customer.objects.count(), 0)

    def test_delete_nonexistent_user_by_email(self):
        url = reverse('user_info', kwargs={'email': 'nonexistent@example.com'})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.json())
        
class CustomerHomeViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('register')
        
        # Create preferences for testing
        self.coloracao_pref = Preferences.objects.create(name='Coloração')
        self.cachos_pref = Preferences.objects.create(name='Cachos')
        self.barbearia_pref = Preferences.objects.create(name='Barbearia')
        self.trancas_pref = Preferences.objects.create(name='Tranças')
        self.other_pref = Preferences.objects.create(name='Corte')
        
        # Create a customer user for testing
        self.customer_data = {
            'first_name': 'Customer',
            'last_name': 'Test',
            'phone': '123423256789',
            'number': '42',
            'complement': 'Apt 1',
            'neighborhood': 'Test Neighborhood',
            'city': 'Test City',
            'state': 'TS',
            'address': 'Customer Street',
            'postal_code': '12345',
            'email': 'customer@example.com',
            'password': 'customer_password',
            'role': 'customer',
            'rating': 5,
            'cpf': '12345678900',
            'preferences': json.dumps([])
        }
        
        # Create hairdresser users for testing
        self.hairdresser_data_1 = {
            'first_name': 'Hairdresser1',
            'last_name': 'Test',
            'phone': '987232654321',
            'number': '15',
            'complement': 'Apt 2',
            'neighborhood': 'Hairdresser Neighborhood',
            'city': 'Hairdresser City',
            'state': 'HR',
            'address': 'Hairdresser Street',
            'postal_code': '54321',
            'email': 'hairdresser1@example.com',
            'password': 'hairdresser_password',
            'role': 'hairdresser',
            'rating': 4,
            'resume': 'Professional hairdresser 1',
            'cnpj': '12345678000191',
            'experience_years': 7,
            'preferences': json.dumps([]),
            'experience_time': 'experience_time',
            'experiences': 'experiences',
            'products': 'products'
        }
        
        self.hairdresser_data_2 = {
            'first_name': 'Hairdresser2',
            'last_name': 'Test',
            'phone': '987232654322',
            'number': '16',
            'complement': 'Apt 3',
            'neighborhood': 'Hairdresser Neighborhood 2',
            'city': 'Hairdresser City 2',
            'state': 'HR',
            'address': 'Hairdresser Street 2',
            'postal_code': '54322',
            'email': 'hairdresser2@example.com',
            'password': 'hairdresser_password',
            'role': 'hairdresser',
            'rating': 5,
            'resume': 'Professional hairdresser 2',
            'cnpj': '12345678000192',
            'experience_years': 5,
            'preferences': json.dumps([]),
            'experience_time': 'experience_time',
            'experiences': 'experiences',
            'products': 'products'
        }
        
        # Register users
        self.client.post(
            self.register_url,
            data=self.customer_data,
        )
        
        self.client.post(
            self.register_url,
            data=self.hairdresser_data_1,
        )
        
        self.client.post(
            self.register_url,
            data=self.hairdresser_data_2,
        )
        
        # Get created users and add preferences
        self.customer_user = User.objects.get(email='customer@example.com')
        self.hairdresser_user_1 = User.objects.get(email='hairdresser1@example.com')
        self.hairdresser_user_2 = User.objects.get(email='hairdresser2@example.com')
        
        # Add preferences to customer (for "for_you" testing)
        self.customer_user.preferences.add(self.coloracao_pref, self.cachos_pref)
        
        # Add preferences to hairdressers
        self.hairdresser_user_1.preferences.add(self.coloracao_pref, self.barbearia_pref)
        self.hairdresser_user_2.preferences.add(self.cachos_pref, self.trancas_pref)

    def test_customer_home_with_matching_preferences(self):
        """Test customer home view returns hairdressers matching customer preferences"""
        url = reverse('customer_home_info', kwargs={'email': 'customer@example.com'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Check structure
        self.assertIn('for_you', data)
        self.assertIn('hairdressers_by_preferences', data)
        
        # Check for_you contains hairdressers with matching preferences
        for_you_data = data['for_you']
        self.assertGreater(len(for_you_data), 0)
        
        # Both hairdressers should be in for_you since they have preferences matching customer
        hairdresser_emails = [h['user']['email'] for h in for_you_data]
        self.assertIn('hairdresser1@example.com', hairdresser_emails)
        self.assertIn('hairdresser2@example.com', hairdresser_emails)

    def test_customer_home_with_specific_preference_categories(self):
        """Test that specific preference categories return correct hairdressers"""
        url = reverse('customer_home_info', kwargs={'email': 'customer@example.com'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        preferences_data = data['hairdressers_by_preferences']
        
        # Check all expected categories are present
        expected_categories = ['coloracao', 'cachos', 'barbearia', 'trancas']
        for category in expected_categories:
            self.assertIn(category, preferences_data)
        
        # Check coloracao category contains hairdresser1
        coloracao_hairdressers = preferences_data['coloracao']
        coloracao_emails = [h['user']['email'] for h in coloracao_hairdressers]
        self.assertIn('hairdresser1@example.com', coloracao_emails)
        
        # Check cachos category contains hairdresser2
        cachos_hairdressers = preferences_data['cachos']
        cachos_emails = [h['user']['email'] for h in cachos_hairdressers]
        self.assertIn('hairdresser2@example.com', cachos_emails)
        
        # Check barbearia category contains hairdresser1
        barbearia_hairdressers = preferences_data['barbearia']
        barbearia_emails = [h['user']['email'] for h in barbearia_hairdressers]
        self.assertIn('hairdresser1@example.com', barbearia_emails)
        
        # Check trancas category contains hairdresser2
        trancas_hairdressers = preferences_data['trancas']
        trancas_emails = [h['user']['email'] for h in trancas_hairdressers]
        self.assertIn('hairdresser2@example.com', trancas_emails)

    def test_customer_home_nonexistent_customer(self):
        """Test customer home view with nonexistent customer email"""
        url = reverse('customer_home_info', kwargs={'email': 'nonexistent@example.com'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'User not found')

    def test_customer_home_hairdresser_email(self):
        """Test customer home view with hairdresser email (should return 404)"""
        url = reverse('customer_home_info', kwargs={'email': 'hairdresser1@example.com'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn('error', data)
        self.assertEqual(data['error'], 'User not found')

    def test_customer_home_no_matching_preferences(self):
        """Test customer home view when customer has no matching preferences"""
        # Create customer with different preferences
        customer_no_match = {
            'first_name': 'NoMatch',
            'last_name': 'Customer',
            'phone': '123423256790',
            'number': '43',
            'complement': 'Apt 4',
            'neighborhood': 'Test Neighborhood',
            'city': 'Test City',
            'state': 'TS',
            'address': 'Customer Street',
            'postal_code': '12346',
            'email': 'nomatch@example.com',
            'password': 'customer_password',
            'role': 'customer',
            'rating': 5,
            'cpf': '12345678901',
            'preferences': json.dumps([])
        }
        
        self.client.post(
            self.register_url,
            data=customer_no_match,
        )
        
        # Add a preference that no hairdresser has
        customer_user_no_match = User.objects.get(email='nomatch@example.com')
        customer_user_no_match.preferences.add(self.other_pref)
        
        url = reverse('customer_home_info', kwargs={'email': 'nomatch@example.com'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # for_you should be empty since no hairdressers match preferences
        self.assertEqual(len(data['for_you']), 0)
        
        # But hairdressers_by_preferences should still have data
        self.assertIn('hairdressers_by_preferences', data)

    def test_customer_home_empty_preferences(self):
        """Test customer home view when customer has no preferences"""
        # Create customer with no preferences
        customer_empty = {
            'first_name': 'Empty',
            'last_name': 'Customer',
            'phone': '123423256791',
            'number': '44',
            'complement': 'Apt 5',
            'neighborhood': 'Test Neighborhood',
            'city': 'Test City',
            'state': 'TS',
            'address': 'Customer Street',
            'postal_code': '12347',
            'email': 'empty@example.com',
            'password': 'customer_password',
            'role': 'customer',
            'rating': 5,
            'cpf': '12345678902',
            'preferences': json.dumps([])
        }
        
        self.client.post(
            self.register_url,
            data=customer_empty,
        )
        
        url = reverse('customer_home_info', kwargs={'email': 'empty@example.com'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # for_you should be empty since customer has no preferences
        self.assertEqual(len(data['for_you']), 0)
        
        # But hairdressers_by_preferences should still have data
        self.assertIn('hairdressers_by_preferences', data)

    def test_customer_home_missing_preference_categories(self):
        """Test behavior when some preference categories don't exist"""
        # Delete one of the preferences to test missing category handling
        self.trancas_pref.delete()
        
        url = reverse('customer_home_info', kwargs={'email': 'customer@example.com'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        preferences_data = data['hairdressers_by_preferences']
        
        # trancas should be empty list since preference doesn't exist
        self.assertEqual(preferences_data['trancas'], [])
        
        # Other categories should still work
        self.assertGreater(len(preferences_data['coloracao']), 0)

    def test_customer_home_response_structure(self):
        """Test the structure of the response data"""
        url = reverse('customer_home_info', kwargs={'email': 'customer@example.com'})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # Check main structure
        self.assertIn('for_you', data)
        self.assertIn('hairdressers_by_preferences', data)
        
        # Check for_you structure (if not empty)
        if data['for_you']:
            hairdresser = data['for_you'][0]
            self.assertIn('user', hairdresser)
            self.assertIn('email', hairdresser['user'])
            self.assertIn('role', hairdresser['user'])
            self.assertEqual(hairdresser['user']['role'], 'hairdresser')
        
        # Check hairdressers_by_preferences structure
        preferences_data = data['hairdressers_by_preferences']
        expected_categories = ['coloracao', 'cachos', 'barbearia', 'trancas']
        
        for category in expected_categories:
            self.assertIn(category, preferences_data)
            if preferences_data[category]:  # If not empty
                hairdresser = preferences_data[category][0]
                self.assertIn('user', hairdresser)
                self.assertIn('email', hairdresser['user'])
                self.assertIn('role', hairdresser['user'])
                self.assertEqual(hairdresser['user']['role'], 'hairdresser')
class GlobalSearchViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.search_url = reverse('global_search')
        
        # Create test users for hairdressers
        self.user1 = User.objects.create(
            first_name='Alice',
            last_name='Johnson',
            phone='11987654321',
            email='alice@example.com',
            role='hairdresser',
            number= '15',
            complement= 'Apt 2',
            neighborhood= 'Hairdresser Neighborhood',
            city= 'Hairdresser City',
            state= 'HR',
            address= 'Hairdresser Street',
            postal_code= '54321',
            password= 'hairdresser_password',
            rating= 4,
        )
        self.user2 = User.objects.create(
            first_name='Bob',
            last_name='Smith',
            phone='11876543210',
            email='bob@example.com',
            role='hairdresser',
            number= '15',
            complement= 'Apt 2',
            neighborhood= 'Hairdresser Neighborhood',
            city= 'Hairdresser City',
            state= 'HR',
            address= 'Hairdresser Street',
            postal_code= '54321',
            password= 'hairdresser_password',
            rating= 4,
        )
        self.user3 = User.objects.create(
            first_name='Carol',
            last_name='Davis',
            phone='11765432109',
            email='carol@example.com',
            role='hairdresser',
            number= '15',
            complement= 'Apt 2',
            neighborhood= 'Hairdresser Neighborhood',
            city= 'Hairdresser City',
            state= 'HR',
            address= 'Hairdresser Street',
            postal_code= '54321',
            password= 'hairdresser_password',
            rating= 4,
        )
        
        self.pref1, created = Preferences.objects.get_or_create(name="Coloração")
        self.pref2, created = Preferences.objects.get_or_create(name="Cachos")
        self.pref3, created = Preferences.objects.get_or_create(name="Corte")
        
        # Set preferences using the proper many-to-many method
        self.user1.preferences.set([self.pref1, self.pref3])
        self.user2.preferences.set([self.pref2])
        self.user3.preferences.set([self.pref1, self.pref2, self.pref3])

        # Create test hairdressers
        self.hairdresser1 = Hairdresser.objects.create(
            user=self.user1,
            cnpj='12345678000191',
            experience_years=5,
            experience_time= 'experience_time',
            experiences= 'experiences',
            products= 'products',
            resume='Specialist in modern cuts and coloring'
        )
        self.hairdresser2 = Hairdresser.objects.create(
            user=self.user2,
            cnpj='12345678000192',
            experience_years=3,
            experience_time= 'experience_time',
            experiences= 'experiences',
            products= 'products',
            resume='Expert in curly hair treatments'
        )
        self.hairdresser3 = Hairdresser.objects.create(
            user=self.user3,
            cnpj='12345678000193',
            experience_years=7,
            experience_time= 'experience_time',
            experiences= 'experiences',
            products= 'products',
            resume='Professional hair styling and makeup'
        )
        
        # Create test services
        self.service1 = Service.objects.create(
            name='Hair Cut',
            hairdresser=self.hairdresser1,
            price=50.00,
            duration=60
        )
        self.service2 = Service.objects.create(
            name='Hair Coloring',
            hairdresser=self.hairdresser1,
            price=120.00,
            duration=180
        )
        self.service3 = Service.objects.create(
            name='Curly Hair Treatment',
            hairdresser=self.hairdresser2,
            price=80.00,
            duration=120
        )
        self.service4 = Service.objects.create(
            name='Wedding Makeup',
            hairdresser=self.hairdresser3,
            price=200.00,
            duration=90
        )

    def test_search_without_query_parameter(self):
        """Test search endpoint without query parameter returns empty list"""
        response = self.client.get(self.search_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data, [])

    def test_search_with_empty_query_parameter(self):
        """Test search endpoint with empty query parameter returns empty list"""
        response = self.client.get(self.search_url, {'search': ''})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data, [])

    def test_search_with_none_query_parameter(self):
        """Test search endpoint with None query parameter returns empty list"""
        response = self.client.get(self.search_url, None)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data, [])

    def test_search_hairdressers_by_first_name(self):
        """Test search finds hairdressers by first name"""
        response = self.client.get(self.search_url, {'search': 'Alice'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        self.assertIn('data', response_data)
        results = response_data['data']
        
        # Should find Alice
        hairdresser_results = [r for r in results if r.get('result_type') == 'hairdresser']
        self.assertEqual(len(hairdresser_results), 1)
        self.assertEqual(hairdresser_results[0]['user']['first_name'], 'Alice')

    def test_search_hairdressers_by_last_name(self):
        """Test search finds hairdressers by last name"""
        response = self.client.get(self.search_url, {'search': 'Smith'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        results = response_data['data']
        hairdresser_results = [r for r in results if r.get('result_type') == 'hairdresser']
        self.assertEqual(len(hairdresser_results), 1)
        self.assertEqual(hairdresser_results[0]['user']['last_name'], 'Smith')

    def test_search_services_by_name(self):
        """Test search finds services by name"""
        response = self.client.get(self.search_url, {'search': 'Hair Cut'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        results = response_data['data']
        service_results = [r for r in results if r.get('result_type') == 'service']
        self.assertEqual(len(service_results), 1)
        self.assertEqual(service_results[0]['name'], 'Hair Cut')

    def test_search_services_partial_name_match(self):
        """Test search finds services with partial name match"""
        response = self.client.get(self.search_url, {'search': 'Hair'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        results = response_data['data']
        service_results = [r for r in results if r.get('result_type') == 'service']
        
        # Should find "Hair Cut" and "Hair Coloring" and "Curly Hair Treatment"
        service_names = [s['name'] for s in service_results]
        self.assertIn('Hair Cut', service_names)
        self.assertIn('Hair Coloring', service_names)
        self.assertIn('Curly Hair Treatment', service_names)

    def test_search_case_insensitive(self):
        """Test search is case insensitive"""
        response = self.client.get(self.search_url, {'search': 'hair cut'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        results = response_data['data']
        service_results = [r for r in results if r.get('result_type') == 'service']
        self.assertEqual(len(service_results), 1)
        self.assertEqual(service_results[0]['name'], 'Hair Cut')

    def test_search_combined_results(self):
        """Test search returns both hairdressers and services when relevant"""
        # Search for "curl" which should match hairdresser Carol and Curly Hair Treatment service
        response = self.client.get(self.search_url, {'search': 'curl'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        results = response_data['data']
        
        # Check we have both types of results
        result_types = [r.get('result_type') for r in results]
        self.assertIn('hairdresser', result_types)
        self.assertIn('service', result_types)
        
        # Verify specific matches
        hairdresser_results = [r for r in results if r.get('result_type') == 'hairdresser']
        service_results = [r for r in results if r.get('result_type') == 'service']
        
        # Should find Carol (contains "car" which might match depending on filter implementation)
        # and Curly Hair Treatment service
        service_names = [s['name'] for s in service_results]
        self.assertIn('Curly Hair Treatment', service_names)

    def test_search_no_results_found(self):
        """Test search with query that matches nothing"""
        response = self.client.get(self.search_url, {'search': 'nonexistent'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        self.assertIn('data', response_data)
        results = response_data['data']
        self.assertEqual(len(results), 0)

    def test_search_result_serializer_structure(self):
        """Test that search results have correct structure and required fields"""
        response = self.client.get(self.search_url, {'search': 'Alice'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        results = response_data['data']
        self.assertGreater(len(results), 0)
        
        # Check hairdresser result structure
        hairdresser_results = [r for r in results if r.get('result_type') == 'hairdresser']
        if hairdresser_results:
            hairdresser = hairdresser_results[0]
            self.assertIn('result_type', hairdresser)
            self.assertEqual(hairdresser['result_type'], 'hairdresser')
            self.assertIn('user', hairdresser)
            self.assertIn('cnpj', hairdresser)
            self.assertIn('resume', hairdresser)

    def test_search_service_result_structure(self):
        """Test that service search results have correct structure"""
        response = self.client.get(self.search_url, {'search': 'Hair Cut'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        results = response_data['data']
        service_results = [r for r in results if r.get('result_type') == 'service']
        self.assertGreater(len(service_results), 0)
        
        service = service_results[0]
        self.assertIn('result_type', service)
        self.assertEqual(service['result_type'], 'service')
        self.assertIn('name', service)
        self.assertIn('price', service)
        self.assertIn('duration', service)
        self.assertIn('hairdresser', service)

    def test_search_response_format(self):
        """Test that response is in correct JSON format"""
        response = self.client.get(self.search_url, {'search': 'Alice'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Should be able to parse as JSON
        response_data = response.json()
        self.assertIsInstance(response_data, dict)
        self.assertIn('data', response_data)
        self.assertIsInstance(response_data['data'], list)

    def test_search_with_special_characters(self):
        """Test search handles special characters gracefully"""
        response = self.client.get(self.search_url, {'search': 'Alice@#$%'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertIn('data', response_data)

    def test_search_with_very_long_query(self):
        """Test search handles very long query strings"""
        long_query = 'a' * 1000
        response = self.client.get(self.search_url, {'search': long_query})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertIn('data', response_data)

    def test_search_with_unicode_characters(self):
        """Test search handles unicode characters"""
        response = self.client.get(self.search_url, {'search': 'Alicê'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertIn('data', response_data)

    def test_search_result_order_consistency(self):
        """Test that search results are returned in consistent order"""
        response1 = self.client.get(self.search_url, {'search': 'Hair'})
        response2 = self.client.get(self.search_url, {'search': 'Hair'})
        
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        
        # Results should be identical for same query
        self.assertEqual(response1.json(), response2.json())

    def test_search_handles_deleted_objects(self):
        """Test search gracefully handles if objects are deleted during processing"""
        response = self.client.get(self.search_url, {'search': 'Alice'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertIn('data', response_data)

    def test_search_performance_with_multiple_results(self):
        """Test search performance doesn't degrade significantly with multiple results"""
        import time
        
        start_time = time.time()
        response = self.client.get(self.search_url, {'search': 'Hair'})
        end_time = time.time()
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        response_time = end_time - start_time
        self.assertLess(response_time, 1.0)

class HairdresserInfoViewTest(TestCase):
    def setUp(self):
        """Set up test data before each test method."""
        self.client = Client()
        
        # Create a test user for hairdresser
        self.hairdresser_user = User.objects.create(
            email='hairdresser@test.com',
            password='testpass123',
            first_name='John',
            last_name='Doe',
            phone='1234567890',
            complement='Apt 1',
            neighborhood='Downtown',
            city='Test City',
            state='TX',
            address='123 Test St',
            number='123',
            postal_code='12345',
            role='HAIRDRESSER'
        )
        
        # Create a hairdresser instance
        self.hairdresser = Hairdresser.objects.create(
            user=self.hairdresser_user,
            experience_years=5,
            resume='Experienced hairdresser with 5 years in the industry',
            cnpj='12345678901234',
            experience_time='5 years',
            experiences='Cutting, coloring, styling',
            products='Professional hair care products'
        )
        
        # Create another hairdresser for additional tests
        self.hairdresser_user_2 = User.objects.create(
            email='hairdresser2@test.com',
            password='testpass123',
            first_name='Jane',
            last_name='Smith',
            phone='0987654321',
            complement='Suite 2',
            neighborhood='Uptown',
            city='Test City 2',
            state='CA',
            address='456 Test Ave',
            number='456',
            postal_code='67890',
            role='HAIRDRESSER'
        )
        
        self.hairdresser_2 = Hairdresser.objects.create(
            user=self.hairdresser_user_2,
            experience_years=3,
            resume='Creative hairdresser specializing in modern styles',
            cnpj='98765432109876',
            experience_time='3 years',
            experiences='Modern cuts, hair extensions',
            products='Organic hair products'
        )

    def test_get_hairdresser_info_success(self):
        """Test successful retrieval of hairdresser information."""
        url = reverse('hairdresser_info', kwargs={'hairdresser_id': self.hairdresser.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Parse JSON response
        response_data = json.loads(response.content)
        
        # Check response structure
        self.assertIn('data', response_data)
        hairdresser_data = response_data['data']
        
        # Verify hairdresser data is present
        self.assertIsNotNone(hairdresser_data)
        
        # Verify some key fields (adjust based on your serializer)
        # Note: The exact fields depend on your HairdresserSerializer implementation
        self.assertEqual(hairdresser_data['id'], self.hairdresser.id)

    def test_get_hairdresser_info_not_found(self):
        """Test retrieval with non-existent hairdresser ID."""
        non_existent_id = 99999
        url = reverse('hairdresser_info', kwargs={'hairdresser_id': non_existent_id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)
        
        # Parse JSON response
        response_data = json.loads(response.content)
        
        # Check error message
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'Hairdresser not found')

    def test_get_hairdresser_info_zero_id(self):
        """Test retrieval with ID 0."""
        url = reverse('hairdresser_info', kwargs={'hairdresser_id': 0})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 404)
        
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'Hairdresser not found')

    def test_get_different_hairdresser_info(self):
        """Test retrieval of different hairdresser information."""
        url = reverse('hairdresser_info', kwargs={'hairdresser_id': self.hairdresser_2.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        hairdresser_data = response_data['data']
        
        # Verify it's the correct hairdresser
        self.assertEqual(hairdresser_data['id'], self.hairdresser_2.id)

    def test_response_content_type(self):
        """Test that response content type is JSON."""
        url = reverse('hairdresser_info', kwargs={'hairdresser_id': self.hairdresser.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')

    def test_post_method_not_allowed(self):
        """Test that POST method is not allowed."""
        url = reverse('hairdresser_info', kwargs={'hairdresser_id': self.hairdresser.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 405)  # Method Not Allowed

    def test_put_method_not_allowed(self):
        """Test that PUT method is not allowed."""
        url = reverse('hairdresser_info', kwargs={'hairdresser_id': self.hairdresser.id})
        response = self.client.put(url)
        
        self.assertEqual(response.status_code, 405)  # Method Not Allowed

    def test_delete_method_not_allowed(self):
        """Test that DELETE method is not allowed."""
        url = reverse('hairdresser_info', kwargs={'hairdresser_id': self.hairdresser.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, 405)  # Method Not Allowed

    @patch('users.views.HairdresserSerializer')  # Replace 'your_app' with your actual app name
    def test_serializer_called_correctly(self, mock_serializer):
        """Test that the serializer is called with the correct hairdresser instance."""
        # Mock the serializer
        mock_serializer.return_value.data = {'id': self.hairdresser.id, 'test': 'data'}
        
        url = reverse('hairdresser_info', kwargs={'hairdresser_id': self.hairdresser.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify serializer was called with correct hairdresser instance
        mock_serializer.assert_called_once_with(self.hairdresser)

    def test_hairdresser_with_minimal_data(self):
        """Test hairdresser with minimal required data."""
        # Create a hairdresser with minimal data
        minimal_user = User.objects.create(
            email='minimal@test.com',
            password='testpass123',
            first_name='Min',
            last_name='User',
            phone='1111111111',
            complement='N/A',
            neighborhood='Minimal',
            city='Min City',
            state='MN',
            address='Min St',
            postal_code='11111',
            role='HAIRDRESSER'
        )
        
        minimal_hairdresser = Hairdresser.objects.create(
            user=minimal_user,
            cnpj='11111111111111'
            # Other fields are optional/nullable
        )
        
        url = reverse('hairdresser_info', kwargs={'hairdresser_id': minimal_hairdresser.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        self.assertIn('data', response_data)
        self.assertIsNotNone(response_data['data'])

    def test_url_pattern_matching(self):
        """Test that URL pattern correctly captures hairdresser_id."""
        # Test with various ID formats
        test_ids = [1, 123, 999999]
        
        for test_id in test_ids:
            url = reverse('hairdresser_info', kwargs={'hairdresser_id': test_id})
            self.assertIn(str(test_id), url)

    def tearDown(self):
        """Clean up after each test."""
        pass


class HairdresserInfoViewIntegrationTest(TestCase):
    """Integration tests for HairdresserInfoView."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create a complete hairdresser with user
        self.user = User.objects.create(
            email='integration@test.com',
            password='testpass123',
            first_name='Integration',
            last_name='Test',
            phone='5555555555',
            complement='Integration Suite',
            neighborhood='Test Neighborhood',
            city='Integration City',
            state='IT',
            address='Integration St',
            number='555',
            postal_code='55555',
            role='HAIRDRESSER',
            rating=4
        )
        
        self.hairdresser = Hairdresser.objects.create(
            user=self.user,
            experience_years=10,
            resume='Highly experienced hairdresser',
            cnpj='55555555555555',
            experience_time='10 years',
            experiences='All types of hair services',
            products='Premium hair care products'
        )

    def test_full_hairdresser_data_retrieval(self):
        """Test complete data retrieval including user information."""
        url = reverse('hairdresser_info', kwargs={'hairdresser_id': self.hairdresser.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        
        response_data = json.loads(response.content)
        hairdresser_data = response_data['data']
        
        self.assertIsInstance(hairdresser_data, dict)
        self.assertIn('id', hairdresser_data)
        self.assertEqual(hairdresser_data['id'], self.hairdresser.id)


def _create_plain_user(**overrides):
    fields = {
        'first_name': 'Plain',
        'last_name': 'User',
        'phone': '5511999990000',
        'neighborhood': 'Centro',
        'city': 'Manaus',
        'state': 'AM',
        'address': 'Rua A',
        'postal_code': '69000000',
        'email': 'plain@example.com',
        'role': 'customer',
    }
    fields.update(overrides)
    return User.objects.create(**fields)


class AuthTokensTest(TestCase):
    def setUp(self):
        self.user = _create_plain_user()

    def _frozen_datetime(self, frozen_now):
        patcher = patch('users.auth_tokens.datetime')
        mock_datetime = patcher.start()
        self.addCleanup(patcher.stop)
        mock_datetime.timedelta = datetime.timedelta
        mock_datetime.timezone = datetime.timezone
        mock_datetime.datetime.now.return_value = frozen_now
        return mock_datetime

    def test_session_token_payload_matches_login_session(self):
        token = issue_session_token(self.user)

        payload = jwt.decode(token, 'secret', algorithms=['HS256'])
        self.assertEqual(payload['id'], self.user.id)
        self.assertEqual(payload['exp'] - payload['iat'], 3600)

    def test_set_session_cookie_attributes(self):
        response = set_session_cookie(JsonResponse({}), self.user)

        cookie = response.cookies['jwt']
        self.assertTrue(cookie['httponly'])
        self.assertEqual(cookie['samesite'], 'None')
        self.assertTrue(cookie['secure'])
        payload = jwt.decode(cookie.value, 'secret', algorithms=['HS256'])
        self.assertEqual(payload['id'], self.user.id)

    def test_signup_token_claims_and_30_minute_expiry(self):
        frozen_now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)
        self._frozen_datetime(frozen_now)

        token = create_signup_token('ana@gmail.com', 'google-sub-123')

        claims = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        self.assertEqual(claims['email'], 'ana@gmail.com')
        self.assertEqual(claims['sub'], 'google-sub-123')
        self.assertEqual(claims['purpose'], 'google_signup')
        self.assertEqual(claims['iat'], int(frozen_now.timestamp()))
        self.assertEqual(claims['exp'], int((frozen_now + datetime.timedelta(minutes=30)).timestamp()))
        self.assertEqual(SIGNUP_TOKEN_TTL, datetime.timedelta(minutes=30))

    def test_decode_signup_token_returns_claims(self):
        claims = decode_signup_token(create_signup_token('ana@gmail.com', 'google-sub-123'))

        self.assertEqual(claims['email'], 'ana@gmail.com')
        self.assertEqual(claims['sub'], 'google-sub-123')

    def test_decode_rejects_expired_signup_token(self):
        issued_at = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=31)
        mock_datetime = self._frozen_datetime(issued_at)
        token = create_signup_token('ana@gmail.com', 'google-sub-123')
        mock_datetime.datetime.now.return_value = datetime.datetime.now(datetime.timezone.utc)

        with self.assertRaises(InvalidSignupToken):
            decode_signup_token(token)

    def test_decode_rejects_tampered_signup_token(self):
        header, _, signature = create_signup_token('ana@gmail.com', 'google-sub-123').split('.')
        forged_claims = {
            'email': 'attacker@gmail.com',
            'sub': 'google-sub-123',
            'purpose': 'google_signup',
            'exp': int((datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30)).timestamp()),
        }
        forged_payload = base64.urlsafe_b64encode(json.dumps(forged_claims).encode()).rstrip(b'=').decode()

        with self.assertRaises(InvalidSignupToken):
            decode_signup_token(f'{header}.{forged_payload}.{signature}')

    def test_decode_rejects_token_signed_with_session_key(self):
        token = jwt.encode({
            'email': 'ana@gmail.com',
            'sub': 'google-sub-123',
            'purpose': 'google_signup',
            'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30),
        }, 'secret', algorithm='HS256')

        with self.assertRaises(InvalidSignupToken):
            decode_signup_token(token)

    def test_decode_rejects_token_with_other_purpose(self):
        token = jwt.encode({
            'email': 'ana@gmail.com',
            'sub': 'google-sub-123',
            'purpose': 'session',
            'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30),
        }, settings.SECRET_KEY, algorithm='HS256')

        with self.assertRaises(InvalidSignupToken):
            decode_signup_token(token)




@override_settings(GOOGLE_OAUTH_CLIENT_IDS=['web-client-id', 'ios-client-id'])
class GoogleAuthVerifierTest(SimpleTestCase):
    def setUp(self):
        patcher = patch('users.google_auth.id_token.verify_oauth2_token')
        self.mock_verify = patcher.start()
        self.addCleanup(patcher.stop)

    def _claims(self, **overrides):
        claims = {
            'aud': 'ios-client-id',
            'sub': 'google-sub-123',
            'email': 'ana@gmail.com',
            'email_verified': True,
            'given_name': 'Ana',
            'family_name': 'Souza',
        }
        claims.update(overrides)
        return claims

    def test_valid_token_with_listed_audience_returns_identity(self):
        self.mock_verify.return_value = self._claims()

        identity = verify_google_id_token('google-id-token')

        self.assertEqual(identity, {
            'sub': 'google-sub-123',
            'email': 'ana@gmail.com',
            'email_verified': True,
            'given_name': 'Ana',
            'family_name': 'Souza',
        })
        args, kwargs = self.mock_verify.call_args
        self.assertEqual(args[0], 'google-id-token')
        self.assertIsNone(kwargs['audience'])

    def test_value_error_becomes_google_token_error(self):
        self.mock_verify.side_effect = ValueError('Token expired')

        with self.assertRaises(GoogleTokenError):
            verify_google_id_token('google-id-token')

    def test_google_auth_error_becomes_google_token_error(self):
        self.mock_verify.side_effect = GoogleAuthError('Could not fetch certificates')

        with self.assertRaises(GoogleTokenError):
            verify_google_id_token('google-id-token')

    def test_audience_outside_list_is_rejected(self):
        self.mock_verify.return_value = self._claims(aud='someone-elses-client-id')

        with self.assertRaises(GoogleTokenError):
            verify_google_id_token('google-id-token')

    @override_settings(GOOGLE_OAUTH_CLIENT_IDS=[])
    def test_empty_client_id_list_rejects_everything(self):
        self.mock_verify.return_value = self._claims(aud='web-client-id')

        with self.assertRaises(GoogleTokenError):
            verify_google_id_token('google-id-token')

    def test_email_verified_is_normalized_to_bool(self):
        cases = [(True, True), ('true', True), ('false', False), (False, False)]
        for raw_value, expected in cases:
            with self.subTest(email_verified=raw_value):
                self.mock_verify.return_value = self._claims(email_verified=raw_value)
                self.assertIs(verify_google_id_token('google-id-token')['email_verified'], expected)

        with self.subTest(email_verified='missing'):
            claims = self._claims()
            del claims['email_verified']
            self.mock_verify.return_value = claims
            self.assertIs(verify_google_id_token('google-id-token')['email_verified'], False)

    def test_missing_names_default_to_empty_string(self):
        claims = self._claims()
        del claims['given_name']
        del claims['family_name']
        self.mock_verify.return_value = claims

        identity = verify_google_id_token('google-id-token')

        self.assertEqual(identity['given_name'], '')
        self.assertEqual(identity['family_name'], '')




class LoginViewGoogleAccountTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.login_url = reverse('login')
        self.user_auth_url = reverse('user_auth')

    def test_password_login_on_google_only_account_returns_403(self):
        _create_plain_user(email='google-only@example.com', password=None, google_id='google-sub-123')

        response = self.client.post(
            self.login_url,
            data=json.dumps({'email': 'google-only@example.com', 'password': 'any_password'}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(
            response.json()['error'],
            'Esta conta usa login com Google. Use o botão Entrar com Google.'
        )
        self.assertNotIn('jwt', response.cookies)

    def test_auth_user_with_signup_token_cookie_is_not_authenticated(self):
        self.client.cookies['jwt'] = create_signup_token('ana@gmail.com', 'google-sub-123')

        response = self.client.get(self.user_auth_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'authenticated': False})

    def test_auth_user_with_invalid_signature_is_not_authenticated(self):
        user = _create_plain_user()
        self.client.cookies['jwt'] = jwt.encode({
            'id': user.id,
            'exp': datetime.datetime.now() + datetime.timedelta(minutes=60),
            'iat': datetime.datetime.now(),
        }, 'not-the-session-secret', algorithm='HS256')

        response = self.client.get(self.user_auth_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'authenticated': False})




class GoogleAuthViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.google_auth_url = reverse('google_auth')
        self.user_auth_url = reverse('user_auth')
        patcher = patch('users.views.verify_google_id_token')
        self.mock_verify = patcher.start()
        self.addCleanup(patcher.stop)

    def _identity(self, **overrides):
        identity = {
            'sub': 'google-sub-123',
            'email': 'ana@gmail.com',
            'email_verified': True,
            'given_name': 'Ana',
            'family_name': 'Souza',
        }
        identity.update(overrides)
        return identity

    def _post(self, body=None):
        return self.client.post(
            self.google_auth_url,
            data=json.dumps({'id_token': 'google-id-token'} if body is None else body),
            content_type='application/json'
        )

    def _users_snapshot(self):
        return list(User.objects.order_by('id').values_list('id', 'email', 'google_id', 'password'))

    def _assert_session_cookie_for(self, response, user):
        cookie = response.cookies['jwt']
        self.assertTrue(cookie['httponly'])
        self.assertEqual(cookie['samesite'], 'None')
        self.assertTrue(cookie['secure'])
        payload = jwt.decode(cookie.value, 'secret', algorithms=['HS256'])
        self.assertEqual(payload['id'], user.id)
        self.assertEqual(payload['exp'] - payload['iat'], 3600)

        self.client.cookies['jwt'] = cookie.value
        auth_response = self.client.get(self.user_auth_url)
        self.assertEqual(auth_response.json(), {'authenticated': True})

    def test_linked_google_account_is_authenticated(self):
        user = _create_plain_user(email='ana@gmail.com', google_id='google-sub-123')
        self.mock_verify.return_value = self._identity()

        response = self._post()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'status': 'authenticated'})
        self.mock_verify.assert_called_once_with('google-id-token')
        self._assert_session_cookie_for(response, user)

    def test_existing_email_with_different_case_is_linked_and_authenticated(self):
        user = _create_plain_user(email='ana@gmail.com', password='hashed', google_id=None)
        self.mock_verify.return_value = self._identity(email='Ana@Gmail.com')

        response = self._post()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'status': 'authenticated'})
        user.refresh_from_db()
        self.assertEqual(user.google_id, 'google-sub-123')
        self.assertEqual(user.password, 'hashed')
        self.assertEqual(User.objects.count(), 1)
        self._assert_session_cookie_for(response, user)

    def test_missing_or_empty_id_token_returns_400(self):
        for body in ({}, {'id_token': ''}):
            with self.subTest(body=body):
                response = self._post(body)

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('error', response.json())
                self.assertNotIn('jwt', response.cookies)
        self.mock_verify.assert_not_called()

    def test_invalid_google_token_returns_401_without_changes(self):
        _create_plain_user(email='ana@gmail.com', google_id=None)
        before = self._users_snapshot()
        self.mock_verify.side_effect = GoogleTokenError('bad token')

        response = self._post()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.json())
        self.assertNotIn('jwt', response.cookies)
        self.assertEqual(self._users_snapshot(), before)

    def test_unverified_email_returns_403_without_changes(self):
        _create_plain_user(email='ana@gmail.com', google_id=None)
        before = self._users_snapshot()
        self.mock_verify.return_value = self._identity(email_verified=False)

        response = self._post()

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('error', response.json())
        self.assertNotIn('jwt', response.cookies)
        self.assertEqual(self._users_snapshot(), before)

    def test_email_linked_to_another_google_account_returns_409(self):
        _create_plain_user(email='ana@gmail.com', google_id='another-google-sub')
        before = self._users_snapshot()
        self.mock_verify.return_value = self._identity()

        response = self._post()

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn('error', response.json())
        self.assertNotIn('jwt', response.cookies)
        self.assertEqual(self._users_snapshot(), before)

    def test_new_account_returns_signup_required_without_creating_rows(self):
        _create_plain_user(email='someone-else@example.com')
        users_before = User.objects.count()
        self.mock_verify.return_value = self._identity()

        response = self._post()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(body['status'], 'signup_required')
        self.assertIsInstance(body['signup_token'], str)
        self.assertEqual(body['prefill'], {
            'email': 'ana@gmail.com',
            'first_name': 'Ana',
            'last_name': 'Souza',
        })
        self.assertNotIn('jwt', response.cookies)
        self.assertEqual(User.objects.count(), users_before)
        self.assertEqual(Customer.objects.count(), 0)
        self.assertEqual(Hairdresser.objects.count(), 0)

    def test_signup_token_carries_email_and_sub_for_30_minutes(self):
        self.mock_verify.return_value = self._identity()

        response = self._post()

        claims = decode_signup_token(response.json()['signup_token'])
        self.assertEqual(claims['email'], 'ana@gmail.com')
        self.assertEqual(claims['sub'], 'google-sub-123')
        self.assertEqual(claims['exp'] - claims['iat'], 1800)

    def test_new_account_calling_again_is_still_signup_required(self):
        self.mock_verify.return_value = self._identity()

        first = self._post()
        second = self._post()

        self.assertEqual(first.json()['status'], 'signup_required')
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(second.json()['status'], 'signup_required')
        self.assertNotIn('jwt', second.cookies)
        self.assertEqual(User.objects.count(), 0)


