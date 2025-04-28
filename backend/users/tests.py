from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
import json
import jwt
import datetime
import bcrypt
from .models import User, Customer, Hairdresser


class RegisterViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('register')
        self.valid_customer_payload = {
            'first_name': 'John',
            'last_name': 'Doe',
            'phone': '123456789',
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
            'cpf': '12345678900'
        }
        self.valid_hairdresser_payload = {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'phone': '987654321',
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
            'experience_years': 5
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
        invalid_payload = self.valid_customer_payload.copy()
        invalid_payload.pop('role')
        
        response = self.client.post(
            self.register_url,
            data=json.dumps(invalid_payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 0)


class LoginViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.user_data = {
            'first_name': 'Test',
            'last_name': 'User',
            'phone': '123456789',
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
            'cpf': '12345678900'
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


class UserInfoViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.user_info_url = reverse('user_info_auth')
        
        # Create customer user
        self.customer_data = {
            'first_name': 'Customer',
            'last_name': 'Test',
            'phone': '123456789',
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
            'cpf': '12345678900'
        }
        
        # Create hairdresser user
        self.hairdresser_data = {
            'first_name': 'Hairdresser',
            'last_name': 'Test',
            'phone': '987654321',
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
            'experience_years': 7
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
        
        response = self.client.get(self.user_info_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        customer_data = response.json()['customer']
        self.assertEqual(customer_data['user']['email'], 'customer@example.com')
        self.assertEqual(customer_data['user']['role'], 'customer')
        self.assertIn('cpf', customer_data)

    def test_get_hairdresser_info(self):
        self.client.cookies['jwt'] = self.hairdresser_token
        
        response = self.client.get(self.user_info_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        hairdresser_data = response.json()['hairdresser']
        self.assertEqual(hairdresser_data['user']['email'], 'hairdresser@example.com')
        self.assertEqual(hairdresser_data['user']['role'], 'hairdresser')
        self.assertIn('resume', hairdresser_data)
        self.assertIn('experience_years', hairdresser_data)

    def test_get_user_info_without_token(self):
        # Ensure no token in cookies
        self.client.cookies.clear()
        
        response = self.client.get(self.user_info_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_user(self):
        self.client.cookies['jwt'] = self.customer_token
        
        response = self.client.delete(self.user_info_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify user is deleted
        self.assertEqual(User.objects.filter(email='customer@example.com').count(), 0)
        self.assertEqual(Customer.objects.count(), 0)

    def test_delete_user_without_token(self):
        self.client.cookies.clear()
        
        response = self.client.delete(self.user_info_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Verify no users were deleted
        self.assertEqual(User.objects.count(), 2)

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
            'phone': '123456789',
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
            'cpf': '12345678900'
        }
        
        # Create hairdresser user
        self.hairdresser_data = {
            'first_name': 'Hairdresser',
            'last_name': 'Test',
            'phone': '987654321',
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
            'experience_years': 7
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
            'phone': '123456789',
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
            'cpf': '12345678900'
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

class DeleteUserByEmailTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('register')
        
        # Create first test user
        self.user1_data = {
            'first_name': 'Test',
            'last_name': 'User1',
            'phone': '123456789',
            'number': '42',
            'complement': 'Apt 1',
            'neighborhood': 'Test Neighborhood',
            'city': 'Test City',
            'state': 'TS',
            'address': 'Test Street',
            'postal_code': '12345',
            'email': 'test1@example.com',
            'password': 'test_password',
            'role': 'customer',
            'rating': 5,
            'cpf': '12345678900'
        }
        
        # Create second test user
        self.user2_data = {
            'first_name': 'Test',
            'last_name': 'User2',
            'phone': '987654321',
            'number': '24',
            'complement': 'Apt 2',
            'neighborhood': 'Another Neighborhood',
            'city': 'Another City',
            'state': 'AC',
            'address': 'Another Street',
            'postal_code': '54321',
            'email': 'test2@example.com',
            'password': 'another_password',
            'role': 'hairdresser',
            'rating': 4,
            'resume': 'Professional hairdresser',
            'cnpj': '12345678000190',
            'experience_years': 3
        }
        
        # Register users
        self.client.post(
            self.register_url,
            data=json.dumps(self.user1_data),
            content_type='application/json'
        )
        
        response = self.client.post(
            self.register_url,
            data=json.dumps(self.user2_data),
            content_type='application/json'
        )
        
        # URLs for deletion tests
        self.delete_user1_url = reverse('user_info', kwargs={'email': 'test1@example.com'})
        self.delete_user2_url = reverse('user_info', kwargs={'email': 'test2@example.com'})
        self.delete_nonexistent_url = reverse('user_info', kwargs={'email': 'nonexistent@example.com'})
        self.delete_no_email_url = reverse('user_info', kwargs={'email': None})
        
        # Setup JWT token for testing cookie-based functionality
        self.login_url = reverse('login')
        login_payload = {
            'email': 'test1@example.com',
            'password': 'test_password'
        }
        
        login_response = self.client.post(
            self.login_url,
            data=json.dumps(login_payload),
            content_type='application/json'
        )
        
        self.token = login_response.data.get('jwt')

    def test_delete_user_by_email_without_token(self):
        """Test deleting a user by email without a token (admin operation)"""
        # Ensure no token in cookies
        self.client.cookies.clear()
        
        # Before deletion
        self.assertEqual(User.objects.filter(email='test1@example.com').count(), 1)
        
        response = self.client.delete(self.delete_user1_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['message'], 'user deleted')
        
        # After deletion
        self.assertEqual(User.objects.filter(email='test1@example.com').count(), 0)
        
        # Verify the cookie wasn't set (since there was no token)
        self.assertNotIn('jwt', response.cookies)

    def test_delete_user_by_email_with_token(self):
        """Test deleting a user by email with a token present in cookies"""
        # Set token in cookies
        self.client.cookies['jwt'] = self.token
        
        # Before deletion
        self.assertEqual(User.objects.filter(email='test2@example.com').count(), 1)
        
        response = self.client.delete(self.delete_user2_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['message'], 'user deleted')
        
        # After deletion
        self.assertEqual(User.objects.filter(email='test2@example.com').count(), 0)
        
        # Verify the cookie was deleted
        if 'jwt' in response.cookies:
            self.assertTrue(response.cookies['jwt'].get('max-age', 0) <= 0)

    def test_delete_nonexistent_user(self):
        """Test deleting a user that doesn't exist"""
        response = self.client.delete(self.delete_nonexistent_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()['error'], 'User not found')

    def test_delete_without_email(self):
        """Test deleting without providing an email"""
        response = self.client.delete(self.delete_no_email_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()['error'], 'User not found')

    def test_delete_inactive_user(self):
        """Test deleting a user that exists but is inactive"""
        # Make user inactive
        user = User.objects.get(email='test1@example.com')
        user.is_active = False
        user.save()
        
        response = self.client.delete(self.delete_user1_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()['error'], 'User not found')
        
        # Verify the user still exists (wasn't deleted)
        self.assertEqual(User.objects.filter(email='test1@example.com').count(), 1)