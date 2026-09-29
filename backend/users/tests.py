from django.test import TestCase, Client, SimpleTestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
import json
import jwt
import datetime
import bcrypt
from .models import User, Customer, Hairdresser, user_profile_picture_path
from hairmatch.image_fixtures import make_image_bytes, make_upload
from preferences.models import Preferences
from service.models import Service
import base64
from unittest.mock import patch, MagicMock
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
import requests as http_requests
from django.core.cache import cache
from .cep_lookup import lookup_cep, InvalidCep, CepNotFound, CepServiceUnavailable
import os
import tempfile
from io import BytesIO, StringIO
from PIL import Image
from django.core.files.storage import default_storage
from django.core.management import call_command
from .management.commands import populate_hairdressers

def stored_image(name):
    """Opens what was actually written to the media storage under `name`."""
    with default_storage.open(name) as stored:
        return Image.open(BytesIO(stored.read()))


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
        payload = self.valid_customer_payload.copy()
        payload['profile_picture'] = make_upload('profile.jpg')

        response = self.client.post(self.register_url, data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        user = User.objects.get(email='john@example.com')
        self.assertEqual(user.profile_picture.name, f'profile_pics/{user.id}/profile.webp')
        self.assertEqual(stored_image(user.profile_picture.name).format, 'WEBP')

    def test_register_with_large_uppercase_picture_is_stored_as_resized_webp(self):
        payload = self.valid_customer_payload.copy()
        payload['profile_picture'] = make_upload('FOTO.JPG', size=(3000, 2000))

        response = self.client.post(self.register_url, data=payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email='john@example.com')
        self.assertEqual(user.profile_picture.name, f'profile_pics/{user.id}/FOTO.webp')
        self.assertEqual(stored_image(user.profile_picture.name).size, (1080, 720))


    INVALID_PICTURE_ERROR = {'error': 'Imagem de perfil inválida.'}

    def _register_with_picture(self, payload, picture):
        return self.client.post(self.register_url, data={**payload, 'profile_picture': picture})

    def _assert_no_rows_created(self):
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(Customer.objects.count(), 0)
        self.assertEqual(Hairdresser.objects.count(), 0)

    def test_register_with_a_file_that_is_not_an_image_returns_400_and_creates_nothing(self):
        picture = SimpleUploadedFile('p.jpg', b'not an image', content_type='image/jpeg')

        response = self._register_with_picture(self.valid_customer_payload, picture)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), self.INVALID_PICTURE_ERROR)
        self._assert_no_rows_created()

    def test_register_hairdresser_with_invalid_picture_creates_no_hairdresser(self):
        picture = SimpleUploadedFile('p.jpg', b'not an image', content_type='image/jpeg')

        response = self._register_with_picture(self.valid_hairdresser_payload, picture)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), self.INVALID_PICTURE_ERROR)
        self._assert_no_rows_created()

    def test_register_can_be_retried_with_the_same_email_after_an_invalid_picture(self):
        bad = SimpleUploadedFile('p.jpg', b'not an image', content_type='image/jpeg')
        self.assertEqual(
            self._register_with_picture(self.valid_customer_payload, bad).status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        response = self._register_with_picture(self.valid_customer_payload, make_upload('retry.jpg'))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.get().email, 'john@example.com')

    def test_register_with_a_truncated_jpeg_returns_400(self):
        noise = Image.frombytes('RGB', (300, 300), os.urandom(300 * 300 * 3))
        jpeg = BytesIO()
        noise.save(jpeg, 'JPEG')
        picture = SimpleUploadedFile('cut.jpg', jpeg.getvalue()[: len(jpeg.getvalue()) // 2])

        response = self._register_with_picture(self.valid_customer_payload, picture)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), self.INVALID_PICTURE_ERROR)
        self._assert_no_rows_created()

    def test_register_with_an_image_over_the_pixel_limit_returns_400(self):
        with patch.object(Image, 'MAX_IMAGE_PIXELS', 10):
            response = self._register_with_picture(self.valid_customer_payload, make_upload('big.jpg'))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), self.INVALID_PICTURE_ERROR)
        self._assert_no_rows_created()

    def test_register_without_a_picture_leaves_the_profile_picture_empty(self):
        response = self.client.post(self.register_url, data=self.valid_customer_payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(User.objects.get().profile_picture)


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


class GoogleRegisterTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('register')
        self.user_auth_url = reverse('user_auth')
        self.user_info_auth_url = reverse('user_info_auth')
        self.signup_token = create_signup_token('ana@gmail.com', 'google-sub-123')
        self.customer_payload = {
            'google_signup_token': self.signup_token,
            'first_name': 'Ana',
            'last_name': 'Souza',
            'phone': '92991234567',
            'number': '10',
            'complement': 'Casa',
            'neighborhood': 'Centro',
            'city': 'Manaus',
            'state': 'AM',
            'address': 'Rua A',
            'postal_code': '69000000',
            'role': 'customer',
            'cpf': '12345678900',
            'preferences': json.dumps([]),
        }
        self.hairdresser_payload = {
            **self.customer_payload,
            'role': 'hairdresser',
            'cnpj': '12345678000190',
            'experience_time': '5 anos',
            'experiences': 'Coloração e cortes',
            'products': 'Produtos veganos',
            'resume': 'Especialista em cachos',
        }
        del self.hairdresser_payload['cpf']

    def _assert_no_new_rows(self, users=0):
        self.assertEqual(User.objects.count(), users)
        self.assertEqual(Customer.objects.count(), 0)
        self.assertEqual(Hairdresser.objects.count(), 0)
        self.assertEqual(User.preferences.through.objects.count(), 0)

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

    def test_google_customer_signup_creates_user_customer_and_session(self):
        pref1 = Preferences.objects.create(name='Coloração')
        pref2 = Preferences.objects.create(name='Cachos')
        payload = {**self.customer_payload, 'preferences': json.dumps([pref1.id, pref2.id])}

        response = self.client.post(self.register_url, data=payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get()
        self.assertEqual(user.email, 'ana@gmail.com')
        self.assertIsNone(user.password)
        self.assertEqual(user.google_id, 'google-sub-123')
        self.assertEqual(user.role, 'customer')
        self.assertEqual(user.phone, '5592991234567')
        self.assertEqual(Customer.objects.get(user=user).cpf, '12345678900')
        self.assertEqual(Hairdresser.objects.count(), 0)
        self.assertCountEqual(user.preferences.values_list('id', flat=True), [pref1.id, pref2.id])
        self._assert_session_cookie_for(response, user)

    def test_google_signup_with_profile_picture_stores_a_webp(self):
        payload = {**self.customer_payload, 'profile_picture': make_upload('ana_google.png', fmt='PNG')}

        response = self.client.post(self.register_url, data=payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get()
        self.assertEqual(user.profile_picture.name, f'profile_pics/{user.id}/ana_google.webp')
        self.assertEqual(stored_image(user.profile_picture.name).format, 'WEBP')

    def test_google_signup_with_a_file_that_is_not_an_image_returns_400_without_session(self):
        picture = SimpleUploadedFile('p.jpg', b'not an image', content_type='image/jpeg')

        response = self.client.post(
            self.register_url, data={**self.customer_payload, 'profile_picture': picture}
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json(), {'error': 'Imagem de perfil inválida.'})
        self.assertNotIn('jwt', response.cookies)
        self._assert_no_new_rows()

    def test_google_hairdresser_signup_creates_user_hairdresser_and_session(self):
        response = self.client.post(self.register_url, data=self.hairdresser_payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get()
        self.assertEqual(user.email, 'ana@gmail.com')
        self.assertIsNone(user.password)
        self.assertEqual(user.google_id, 'google-sub-123')
        self.assertEqual(user.role, 'hairdresser')
        hairdresser = Hairdresser.objects.get(user=user)
        self.assertEqual(hairdresser.cnpj, '12345678000190')
        self.assertEqual(hairdresser.experience_time, '5 anos')
        self.assertEqual(hairdresser.experiences, 'Coloração e cortes')
        self.assertEqual(hairdresser.products, 'Produtos veganos')
        self.assertEqual(hairdresser.resume, 'Especialista em cachos')
        self.assertEqual(Customer.objects.count(), 0)
        self._assert_session_cookie_for(response, user)

    def test_form_email_and_password_are_ignored(self):
        payload = {
            **self.customer_payload,
            'email': 'someone-else@example.com',
            'password': 'form_password',
            'confirmPassword': 'form_password',
        }

        response = self.client.post(self.register_url, data=payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get()
        self.assertEqual(user.email, 'ana@gmail.com')
        self.assertIsNone(user.password)
        self.assertFalse(User.objects.filter(email='someone-else@example.com').exists())

    def test_expired_or_tampered_signup_token_returns_401(self):
        issued_at = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=31)
        with patch('users.auth_tokens.datetime') as mock_datetime:
            mock_datetime.timedelta = datetime.timedelta
            mock_datetime.timezone = datetime.timezone
            mock_datetime.datetime.now.return_value = issued_at
            expired_token = create_signup_token('ana@gmail.com', 'google-sub-123')

        header, _, signature = self.signup_token.split('.')
        forged_claims = {
            'email': 'attacker@gmail.com',
            'sub': 'google-sub-123',
            'purpose': 'google_signup',
            'exp': int((datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30)).timestamp()),
        }
        forged_payload = base64.urlsafe_b64encode(json.dumps(forged_claims).encode()).rstrip(b'=').decode()
        tampered_token = f'{header}.{forged_payload}.{signature}'

        for label, token in (('expired', expired_token), ('tampered', tampered_token)):
            with self.subTest(token=label):
                payload = {**self.customer_payload, 'google_signup_token': token}

                response = self.client.post(self.register_url, data=payload)

                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
                self.assertIn('error', response.json())
                self.assertNotIn('jwt', response.cookies)
                self._assert_no_new_rows()

    def test_phone_already_registered_with_country_prefix_returns_409(self):
        _create_plain_user(email='other@example.com', phone='5592991234567')

        response = self.client.post(self.register_url, data=self.customer_payload)

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn('error', response.json())
        self.assertNotIn('jwt', response.cookies)
        self._assert_no_new_rows(users=1)

    def test_email_or_google_sub_already_registered_returns_409(self):
        existing_accounts = (
            ('email', {'email': 'ANA@gmail.com', 'phone': '5511911110000'}),
            ('sub', {'email': 'other@example.com', 'phone': '5511922220000', 'google_id': 'google-sub-123'}),
        )
        for label, fields in existing_accounts:
            with self.subTest(existing=label):
                existing = _create_plain_user(**fields)

                response = self.client.post(self.register_url, data=self.customer_payload)

                self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
                self.assertIn('error', response.json())
                self.assertNotIn('jwt', response.cookies)
                self._assert_no_new_rows(users=1)
                existing.delete()

    def test_missing_required_field_or_invalid_role_returns_400(self):
        customer_fields = ['role', 'first_name', 'last_name', 'phone', 'address',
                           'neighborhood', 'city', 'state', 'postal_code', 'cpf']
        cases = [(f'customer without {field}', self.customer_payload, field) for field in customer_fields]
        cases.append(('hairdresser without cnpj', self.hairdresser_payload, 'cnpj'))

        for label, base_payload, missing_field in cases:
            with self.subTest(case=label):
                payload = {k: v for k, v in base_payload.items() if k != missing_field}

                response = self.client.post(self.register_url, data=payload)

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('error', response.json())
                self._assert_no_new_rows()

        invalid_values = (('invalid role', {'role': 'admin'}), ('short phone', {'phone': '929912345'}))
        for label, override in invalid_values:
            with self.subTest(case=label):
                response = self.client.post(self.register_url, data={**self.customer_payload, **override})

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('error', response.json())
                self._assert_no_new_rows()

    def test_invalid_preferences_json_rolls_back_everything(self):
        for label, base_payload in (('customer', self.customer_payload), ('hairdresser', self.hairdresser_payload)):
            with self.subTest(role=label):
                payload = {**base_payload, 'preferences': 'not-json'}

                response = self.client.post(self.register_url, data=payload)

                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('error', response.json())
                self.assertNotIn('jwt', response.cookies)
                self._assert_no_new_rows()

    def test_error_after_preferences_are_linked_rolls_back_everything(self):
        preference = Preferences.objects.create(name='Cachos')
        payload = {**self.customer_payload, 'preferences': json.dumps([preference.id])}

        with patch.object(Customer.objects, 'create', side_effect=RuntimeError('database failure')):
            response = self.client.post(self.register_url, data=payload)

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.json(), {'error': 'Erro ao criar a conta.'})
        self.assertNotIn('jwt', response.cookies)
        self._assert_no_new_rows()

    def test_end_to_end_google_signup_then_authenticated_profile(self):
        cases = (
            ('customer', self.customer_payload, 'google-sub-customer', 'cliente@gmail.com', '92990000001'),
            ('hairdresser', self.hairdresser_payload, 'google-sub-hairdresser', 'profissional@gmail.com', '92990000002'),
        )
        for role, base_payload, sub, email, phone in cases:
            with self.subTest(role=role):
                client = APIClient()
                identity = {
                    'sub': sub,
                    'email': email,
                    'email_verified': True,
                    'given_name': 'Ana',
                    'family_name': 'Souza',
                }
                with patch('users.views.verify_google_id_token', return_value=identity):
                    google_response = client.post(
                        reverse('google_auth'),
                        data=json.dumps({'id_token': 'google-id-token'}),
                        content_type='application/json'
                    )
                self.assertEqual(google_response.json()['status'], 'signup_required')

                payload = {
                    **base_payload,
                    'google_signup_token': google_response.json()['signup_token'],
                    'phone': phone,
                }
                register_response = client.post(self.register_url, data=payload)
                self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)

                client.cookies['jwt'] = register_response.cookies['jwt'].value
                profile_response = client.get(self.user_info_auth_url)

                self.assertEqual(profile_response.status_code, status.HTTP_200_OK)
                profile = profile_response.json()[role]
                self.assertEqual(profile['user']['email'], email)
                self.assertEqual(profile['user']['role'], role)


class CepLookupServiceTest(TestCase):
    VIACEP_OK = {
        'cep': '69057-000', 'logradouro': 'Avenida Mário Ypiranga', 'complemento': 'até 436/437',
        'bairro': 'Adrianópolis', 'localidade': 'Manaus', 'uf': 'AM', 'ibge': '1302603',
    }
    BRASILAPI_OK = {
        'cep': '69057000', 'state': 'AM', 'city': 'Manaus', 'neighborhood': 'Adrianópolis',
        'street': 'Avenida Mário Ypiranga', 'location': {'coordinates': {}},
    }
    EXPECTED = {
        'postal_code': '69057000', 'address': 'Avenida Mário Ypiranga',
        'neighborhood': 'Adrianópolis', 'city': 'Manaus', 'state': 'AM',
    }

    def setUp(self):
        cache.clear()
        patcher = patch('users.cep_lookup.requests.get')
        self.mock_get = patcher.start()
        self.addCleanup(patcher.stop)

    @staticmethod
    def _response(status_code=200, json_data=None, json_error=False):
        response = MagicMock()
        response.status_code = status_code
        if json_error:
            response.json.side_effect = ValueError('invalid json')
        else:
            response.json.return_value = json_data
        return response

    def _viacep_ok(self):
        return self._response(200, self.VIACEP_OK)

    def test_viacep_found_returns_exact_normalized_dict(self):
        self.mock_get.return_value = self._viacep_ok()
        self.assertEqual(lookup_cep('69057-000'), self.EXPECTED)

    def test_response_has_only_the_five_keys(self):
        self.mock_get.return_value = self._viacep_ok()
        self.assertEqual(
            set(lookup_cep('69057000').keys()),
            {'postal_code', 'address', 'neighborhood', 'city', 'state'},
        )

    def test_invalid_cep_raises_without_calling_provider(self):
        for raw in ['123', '123456789', '']:
            with self.subTest(raw=raw):
                with self.assertRaises(InvalidCep):
                    lookup_cep(raw)
        self.mock_get.assert_not_called()

    def _assert_falls_back_to_brasilapi(self, viacep_side_effect):
        self.mock_get.side_effect = [viacep_side_effect, self._response(200, self.BRASILAPI_OK)]
        self.assertEqual(lookup_cep('69057000'), self.EXPECTED)
        self.assertEqual(self.mock_get.call_count, 2)
        self.assertIn('brasilapi.com.br', self.mock_get.call_args_list[1].args[0])

    def test_viacep_timeout_falls_back_to_brasilapi(self):
        self._assert_falls_back_to_brasilapi(http_requests.Timeout())

    def test_viacep_connection_error_falls_back_to_brasilapi(self):
        self._assert_falls_back_to_brasilapi(http_requests.ConnectionError())

    def test_viacep_status_500_falls_back_to_brasilapi(self):
        self._assert_falls_back_to_brasilapi(self._response(500, None))

    def test_viacep_status_500_with_address_body_falls_back_to_brasilapi(self):
        self._assert_falls_back_to_brasilapi(self._response(500, self.VIACEP_OK))

    def test_viacep_invalid_json_falls_back_to_brasilapi(self):
        self._assert_falls_back_to_brasilapi(self._response(200, json_error=True))

    def test_viacep_erro_string_falls_back_to_brasilapi(self):
        self._assert_falls_back_to_brasilapi(self._response(200, {'erro': 'true'}))

    def test_viacep_erro_boolean_falls_back_to_brasilapi(self):
        self._assert_falls_back_to_brasilapi(self._response(200, {'erro': True}))

    def test_viacep_erro_and_brasilapi_404_raises_not_found(self):
        self.mock_get.side_effect = [self._response(200, {'erro': 'true'}), self._response(404, {})]
        with self.assertRaises(CepNotFound):
            lookup_cep('00000000')

    def test_viacep_timeout_and_brasilapi_404_raises_not_found(self):
        self.mock_get.side_effect = [http_requests.Timeout(), self._response(404, {})]
        with self.assertRaises(CepNotFound):
            lookup_cep('00000000')

    def test_both_providers_failing_raises_service_unavailable(self):
        self.mock_get.side_effect = [http_requests.Timeout(), self._response(500, None)]
        with self.assertRaises(CepServiceUnavailable):
            lookup_cep('69057000')

    def test_every_provider_call_uses_timeout_3(self):
        self.mock_get.side_effect = [http_requests.Timeout(), self._response(200, self.BRASILAPI_OK)]
        lookup_cep('69057000')
        self.assertEqual(self.mock_get.call_count, 2)
        for call in self.mock_get.call_args_list:
            self.assertEqual(call.kwargs['timeout'], 3)

    def test_brasilapi_null_fields_become_empty_strings(self):
        data = dict(self.BRASILAPI_OK, street=None, neighborhood=None)
        self.mock_get.side_effect = [http_requests.Timeout(), self._response(200, data)]
        result = lookup_cep('78175000')
        self.assertEqual(result['address'], '')
        self.assertEqual(result['neighborhood'], '')

    def test_viacep_city_wide_cep_returns_empty_street_and_neighborhood(self):
        data = {'cep': '78175-000', 'logradouro': '', 'bairro': '', 'localidade': 'Poconé', 'uf': 'MT'}
        self.mock_get.return_value = self._response(200, data)
        self.assertEqual(lookup_cep('78175-000'), {
            'postal_code': '78175000', 'address': '', 'neighborhood': '',
            'city': 'Poconé', 'state': 'MT',
        })

    def test_found_cep_is_cached_for_24h(self):
        self.mock_get.return_value = self._viacep_ok()
        with patch('users.cep_lookup.cache.set', wraps=cache.set) as spy_set:
            lookup_cep('69057000')
        spy_set.assert_called_once_with('cep:69057000', self.EXPECTED, 86400)
        self.mock_get.reset_mock()
        self.assertEqual(lookup_cep('69057-000'), self.EXPECTED)
        self.mock_get.assert_not_called()

    def test_not_found_is_not_cached(self):
        self.mock_get.side_effect = [
            self._response(200, {'erro': 'true'}), self._response(404, {}),
            self._response(200, {'erro': 'true'}), self._response(404, {}),
        ]
        for _ in range(2):
            with self.assertRaises(CepNotFound):
                lookup_cep('00000000')
        self.assertEqual(self.mock_get.call_count, 4)

    def test_provider_failure_logs_warning_with_provider_name(self):
        self.mock_get.side_effect = [http_requests.Timeout(), self._response(500, None)]
        with self.assertLogs('users.cep_lookup', 'WARNING') as logs:
            with self.assertRaises(CepServiceUnavailable):
                lookup_cep('69057000')
        self.assertTrue(any('viacep' in line and 'timeout' in line for line in logs.output))
        self.assertTrue(any('brasilapi' in line and 'status 500' in line for line in logs.output))


class CepLookupViewTest(TestCase):
    ADDRESS = {
        'postal_code': '69057000', 'address': 'Avenida Mário Ypiranga',
        'neighborhood': 'Adrianópolis', 'city': 'Manaus', 'state': 'AM',
    }

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        patcher = patch('users.views.lookup_cep')
        self.mock_lookup = patcher.start()
        self.addCleanup(patcher.stop)

    def _get(self, cep='69057-000'):
        return self.client.get(reverse('cep_lookup', args=[cep]))

    def test_route_resolves(self):
        self.assertEqual(reverse('cep_lookup', args=['69057000']), '/api/address/cep/69057000')

    def test_found_cep_returns_200_without_cookie(self):
        self.mock_lookup.return_value = self.ADDRESS
        response = self._get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), self.ADDRESS)
        self.mock_lookup.assert_called_once_with('69057-000')

    def test_invalid_cep_returns_400(self):
        self.mock_lookup.side_effect = InvalidCep('123')
        response = self._get('123')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {'error': 'CEP inválido. Informe 8 dígitos.'})

    def test_not_found_returns_404(self):
        self.mock_lookup.side_effect = CepNotFound('00000000')
        response = self._get('00000000')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {'error': 'CEP não encontrado.'})

    def test_service_unavailable_returns_503(self):
        self.mock_lookup.side_effect = CepServiceUnavailable('69057000')
        response = self._get()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(
            response.json(),
            {'error': 'Serviço de CEP indisponível. Preencha o endereço manualmente.'},
        )

    def test_thirty_first_request_in_a_minute_returns_429(self):
        self.mock_lookup.return_value = self.ADDRESS
        for _ in range(30):
            self.assertEqual(self._get().status_code, 200)
        self.assertEqual(self._get().status_code, 429)


class PopulateHairdressersCommandTest(TestCase):
    PLACEHOLDERS = ['1_hairdresser_placeholder_male.jpg', '1_hairdresser_placeholder_female.jpg']
    PLACEHOLDER_WEBPS = [os.path.splitext(name)[0] + '.webp' for name in PLACEHOLDERS]

    def setUp(self):
        tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_dir.cleanup)
        for file_name in self.PLACEHOLDERS:
            with open(os.path.join(tmp_dir.name, file_name), 'wb') as f:
                f.write(make_image_bytes(size=(64, 48), fmt='JPEG'))
        self.tmp_dir = tmp_dir.name

        patcher = patch.object(populate_hairdressers, 'PLACEHOLDERS_DIR', tmp_dir.name)
        patcher.start()
        self.addCleanup(patcher.stop)

        # The command assigns preference ids 1-17
        Preferences.objects.bulk_create([Preferences(id=i, name=f'pref{i}') for i in range(1, 18)])

    def _run(self):
        call_command('populate_hairdressers', stdout=StringIO())

    def test_uploads_each_hairdresser_picture_to_its_own_directory(self):
        self._run()

        hairdressers = User.objects.filter(role='hairdresser')
        self.assertEqual(hairdressers.count(), 40)
        for user in hairdressers:
            directory, file_name = user.profile_picture.name.rsplit('/', 1)
            self.assertEqual(directory, f'profile_pics/{user.id}')
            self.assertIn(file_name, self.PLACEHOLDER_WEBPS)
            self.assertEqual(stored_image(user.profile_picture.name).format, 'WEBP')

    def test_running_twice_does_not_duplicate_uploads_or_hairdressers(self):
        self._run()
        user = User.objects.filter(role='hairdresser').first()

        self._run()

        _, files = default_storage.listdir(f'profile_pics/{user.id}')
        self.assertEqual(files, [os.path.basename(user.profile_picture.name)])
        self.assertEqual(User.objects.filter(role='hairdresser').count(), 40)

    def test_restores_missing_seeded_pictures_on_the_same_key(self):
        self._run()
        user = User.objects.filter(role='hairdresser').first()
        key = user.profile_picture.name
        default_storage.delete(key)

        self._run()

        self.assertEqual(stored_image(key).format, 'WEBP')
        user.refresh_from_db()
        self.assertEqual(user.profile_picture.name, key)


    def _seeded_hairdresser(self, key_name):
        user = User.objects.create(
            email=f'{key_name}@seed.test', first_name='Seed', last_name='Hairdresser', phone='1',
            neighborhood='n', city='c', state='AM', address='a', postal_code='1', role='hairdresser',
        )
        user.profile_picture = f'profile_pics/{user.id}/{key_name}'
        user.save()
        return user.profile_picture.name

    def test_restores_a_missing_webp_key_with_the_converted_placeholder(self):
        key = self._seeded_hairdresser('1_hairdresser_placeholder_male.webp')

        self._run()

        self.assertEqual(stored_image(key).format, 'WEBP')

    def test_restores_a_missing_legacy_jpg_key_with_the_original_bytes(self):
        key = self._seeded_hairdresser('1_hairdresser_placeholder_male.jpg')

        self._run()

        with open(os.path.join(self.tmp_dir, '1_hairdresser_placeholder_male.jpg'), 'rb') as original:
            expected = original.read()
        with default_storage.open(key) as stored:
            self.assertEqual(stored.read(), expected)

    def test_ignores_a_key_whose_stem_is_not_a_placeholder(self):
        key = self._seeded_hairdresser('not_a_placeholder.webp')

        self._run()

        self.assertFalse(default_storage.exists(key))

class UserProfilePicturePathTest(SimpleTestCase):
    def test_path_is_scoped_by_user_id(self):
        self.assertEqual(
            user_profile_picture_path(User(pk=42), 'screen.png'),
            'profile_pics/42/screen.png',
        )
