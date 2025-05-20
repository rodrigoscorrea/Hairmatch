from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
import json
import jwt
import datetime
import bcrypt
from .models import User, Customer, Hairdresser
from preferences.models import Preferences


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
            'preferences': []  # Add empty preferences list
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
            'preferences': []  # Add empty preferences list
        }

    def test_register_customer_valid(self):
        response = self.client.post(
            self.register_url,
            data=json.dumps(self.valid_customer_payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(Customer.objects.count(), 1)
        self.assertEqual(User.objects.get().email, 'john@example.com')
        self.assertEqual(User.objects.get().role, 'customer')

    def test_register_hairdresser_valid(self):
        response = self.client.post(
            self.register_url,
            data=json.dumps(self.valid_hairdresser_payload),
            content_type='application/json'
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
            data=json.dumps(self.valid_customer_payload),
            content_type='application/json'
        )
        
        # Duplicate registration attempt
        response = self.client.post(
            self.register_url,
            data=json.dumps(self.valid_customer_payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 1)  # No new user created

    def test_register_missing_role(self):
        invalid_payload = self.valid_hairdresser_payload.copy()
        invalid_payload['role'] = ''
        
        response = self.client.post(
            self.register_url,
            data=json.dumps(invalid_payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 0)

    def test_register_missing_password(self):
        invalid_payload = self.valid_hairdresser_payload.copy()
        invalid_payload['password'] = ''
        
        response = self.client.post(
            self.register_url,
            data=json.dumps(invalid_payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 0)

    def test_register_missing_email(self):
        invalid_payload = self.valid_hairdresser_payload.copy()
        invalid_payload['email'] = ''
        
        response = self.client.post(
            self.register_url,
            data=json.dumps(invalid_payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 0)

    def test_register_missing_phone(self):
        invalid_payload = self.valid_hairdresser_payload.copy()
        invalid_payload['phone'] = ''
        
        response = self.client.post(
            self.register_url,
            data=json.dumps(invalid_payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 0)
        
    def test_register_with_short_phone(self):
        invalid_payload = self.valid_hairdresser_payload.copy()
        invalid_payload['phone'] = '1234567890'  # Less than 11 digits
        
        response = self.client.post(
            self.register_url,
            data=json.dumps(invalid_payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 0)

    def test_register_with_preferences(self):
        # Create some test preferences
        pref1 = Preferences.objects.create(name="Coloração")
        pref2 = Preferences.objects.create(name="Cachos")
        
        # Add preference IDs to payload
        payload_with_prefs = self.valid_customer_payload.copy()
        payload_with_prefs['preferences'] = [pref1.id, pref2.id]
        
        response = self.client.post(
            self.register_url,
            data=json.dumps(payload_with_prefs),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        
        # Check if preferences were added to user
        user = User.objects.get(email=payload_with_prefs['email'])
        self.assertEqual(user.preferences.count(), 2)
        self.assertIn(pref1, user.preferences.all())
        self.assertIn(pref2, user.preferences.all())


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
            'preferences': []
        }
        
        # Register user for login tests
        self.client.post(
            self.register_url,
            data=json.dumps(self.user_data),
            content_type='application/json'
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
            'preferences': []
        }
        
        # Register user
        self.client.post(
            self.register_url,
            data=json.dumps(self.user_data),
            content_type='application/json'
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
            'preferences': []
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
            'preferences': []
        }
        
        # Register users
        self.client.post(
            self.register_url,
            data=json.dumps(self.customer_data),
            content_type='application/json'
        )
        
        self.client.post(
            self.register_url,
            data=json.dumps(self.hairdresser_data),
            content_type='application/json'
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
        self.assertIn('experience_years', user_data)

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
            'preferences': []
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
            'preferences': []
        }
        
        # Register users
        self.client.post(
            self.register_url,
            data=json.dumps(self.customer_data),
            content_type='application/json'
        )
        
        self.client.post(
            self.register_url,
            data=json.dumps(self.hairdresser_data),
            content_type='application/json'
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
        self.assertIn('experience_years', user_data)

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
