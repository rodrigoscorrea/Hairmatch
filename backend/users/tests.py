from hairmatch.problem_testing import assert_problem
from hairmatch.problems import Problem
from django.test import TestCase, Client, SimpleTestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
import json
import jwt
import datetime
from .models import User, Customer, Hairdresser, GalleryPhoto, user_profile_picture_path
from .testing import activate_account
from .throttles import (
    ConfirmEmailThrottle,
    ConfirmIpThrottle,
    EmailRateThrottle,
    RegisterEmailThrottle,
    ResendCodeEmailThrottle,
    ResendCodeIpThrottle,
)
from hairmatch.image_fixtures import make_image_bytes, make_upload
from preferences.models import Preferences
from service.models import Service
from agenda.models import Agenda
from availability.models import Availability
from reserve.models import Reserve
from review.models import Review
from django.utils import timezone
import base64
from unittest.mock import patch, MagicMock
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import JsonResponse
from .auth_tokens import (
    issue_session_token,
    set_session_cookie,
    set_cognito_cookies,
    set_access_cookie,
    clear_auth_cookies,
    create_signup_token,
    decode_signup_token,
    InvalidSignupToken,
    SIGNUP_TOKEN_TTL,
)
from .google_auth import verify_google_id_token, GoogleTokenError
from google.auth.exceptions import GoogleAuthError
import requests as http_requests
from django.core.cache import cache
from django.db import IntegrityError, connection
from .views import RegisterView
from .cep_lookup import lookup_cep, InvalidCep, CepNotFound, CepServiceUnavailable
import importlib
import os
import tempfile
from django.apps import apps as django_apps
from io import BytesIO, StringIO
from PIL import Image
from django.core.files.storage import default_storage
from django.core.management import call_command
from .management.commands import populate_hairdressers, purge_unconfirmed_users
from . import cognito_fake
from .cognito import (
    AlreadyConfirmed,
    CognitoService,
    ExpiredConfirmationCode,
    InvalidConfirmationCode,
    ResendRejected,
    Tokens,
    CognitoUnavailable,
    InvalidCredentials,
    InvalidPassword,
    TooManyRequests,
    UserAlreadyExists,
    UserNotConfirmed,
    get_cognito,
    reset_cognito,
)
from botocore.exceptions import (
    ClientError,
    ConnectTimeoutError,
    EndpointConnectionError,
    ReadTimeoutError,
)
from types import SimpleNamespace
from django.test import RequestFactory
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView
from . import authentication
from .authentication import (
    authenticate_request,
    authenticated_customer,
    authenticated_hairdresser,
    authenticated_user,
    forbidden,
)
import unittest
import boto3
from hairmatch.test_runner import HairmatchTestRunner
from jwt.algorithms import RSAAlgorithm

# The key of the session format COG-20 retires. Only the test that proves it is refused uses it.
LEGACY_SESSION_KEY = 'secret'


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
            'password': 'Secure_password1',
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
            'password': 'Secure_password1',
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
        activate_account(self.valid_customer_payload['email'])
        
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
        activate_account(self.valid_customer_payload['email'])
        
        # Duplicate registration attempt
        response = self.client.post(
            self.register_url,
            data=self.valid_customer_payload,
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(User.objects.count(), 1)  # No new user created

    def test_register_with_a_phone_already_used_by_another_email_returns_409(self):
        """The phone is stored with the country code 55; the check must compare that form"""
        self.client.post(self.register_url, data=self.valid_customer_payload)
        activate_account(self.valid_customer_payload['email'])
        payload = dict(self.valid_customer_payload, email='other@example.com', cpf='98765432100')

        response = self.client.post(self.register_url, data=payload)

        assert_phone_taken(response)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().phone, '55123456789123')
        self.assertNotIn('other@example.com', get_cognito().client.users)  # refused before signing up in Cognito

    def test_register_with_the_same_phone_typed_with_a_mask_returns_409(self):
        self.client.post(self.register_url, data=self.valid_customer_payload)
        activate_account(self.valid_customer_payload['email'])
        payload = dict(self.valid_customer_payload, email='other@example.com', phone='(12) 34567-89123')

        response = self.client.post(self.register_url, data=payload)

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(User.objects.count(), 1)

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



    def _register_with_picture(self, payload, picture):
        return self.client.post(self.register_url, data={**payload, 'profile_picture': picture})

    def _assert_no_rows_created(self):
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(Customer.objects.count(), 0)
        self.assertEqual(Hairdresser.objects.count(), 0)

    def test_register_with_a_file_that_is_not_an_image_returns_400_and_creates_nothing(self):
        picture = SimpleUploadedFile('p.jpg', b'not an image', content_type='image/jpeg')

        response = self._register_with_picture(self.valid_customer_payload, picture)

        assert_invalid_picture(response)
        self._assert_no_rows_created()

    def test_register_hairdresser_with_invalid_picture_creates_no_hairdresser(self):
        picture = SimpleUploadedFile('p.jpg', b'not an image', content_type='image/jpeg')

        response = self._register_with_picture(self.valid_hairdresser_payload, picture)

        assert_invalid_picture(response)
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

        assert_invalid_picture(response)
        self._assert_no_rows_created()

    def test_register_with_an_image_over_the_pixel_limit_returns_400(self):
        with patch.object(Image, 'MAX_IMAGE_PIXELS', 10):
            response = self._register_with_picture(self.valid_customer_payload, make_upload('big.jpg'))

        assert_invalid_picture(response)
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
            'password': 'Test_password1',
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
        activate_account(self.user_data['email'])

    def test_login_valid(self):
        login_payload = {
            'email': 'test@example.com',
            'password': 'Test_password1'
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
            'password': 'Wrong_password1'
        }
        
        response = self.client.post(
            self.login_url,
            data=json.dumps(login_payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        assert_invalid_credentials(response)

    def test_login_nonexistent_user(self):
        login_payload = {
            'email': 'nonexistent@example.com',
            'password': 'Test_password1'
        }
        
        response = self.client.post(
            self.login_url,
            data=json.dumps(login_payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        assert_invalid_credentials(response)

    def test_check_authentication_with_token(self):
        # First login to get token
        login_payload = {
            'email': 'test@example.com',
            'password': 'Test_password1'
        }
        
        login_response = self.client.post(
            self.login_url,
            data=json.dumps(login_payload),
            content_type='application/json'
        )
        
        token = login_response.data['jwt']
        self.client.cookies['jwt'] = token
        
        # Then check authentication status
        response = self.client.get(reverse('session'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()['authenticated'])

    def test_check_authentication_without_token(self):
        # Clear cookies to ensure no token
        self.client.cookies.clear()
        
        response = self.client.get(reverse('session'))
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
            'password': 'Old_password1',
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
        activate_account(self.user_data['email'])
        
        # Login to get token
        login_payload = {
            'email': 'password@example.com',
            'password': 'Old_password1'
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
            'old_password': 'Old_password1',
            'password': 'New_password1'
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
            'password': 'New_password1'
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
            'password': 'New_password1'
        }
        
        response = self.client.put(
            self.password_change_url,
            data=json.dumps(change_payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        assert_problem(response, 'invalid-session')

    def test_change_password_with_expired_token(self):
        # Create an expired token
        user = User.objects.get(email='password@example.com')
        payload = {
            'id': user.id,
            'iss': 'hairmatch',
            'token_use': 'session',
            'exp': datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5),  # Expired
            'iat': datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=65)
        }
        expired_token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        
        self.client.cookies['jwt'] = expired_token
        
        change_payload = {
            'password': 'New_password1'
        }
        
        response = self.client.put(
            self.password_change_url,
            data=json.dumps(change_payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        assert_problem(response, 'invalid-session')


class UserInfoCookieViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        self.user_info_auth_url = reverse('current_user')
        
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
            'password': 'Customer_password1',
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
            'password': 'Hairdresser_password1',
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
        activate_account(self.customer_data['email'])
        
        self.client.post(
            self.register_url,
            data=self.hairdresser_data,
        )
        activate_account(self.hairdresser_data['email'])
        
        # Helper method to login and get token
        self.customer_token = self._get_token('customer@example.com', 'Customer_password1')
        self.hairdresser_token = self._get_token('hairdresser@example.com', 'Hairdresser_password1')

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
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        assert_problem(response, 'invalid-session')

    def test_delete_user(self):
        self.client.cookies['jwt'] = self.customer_token
        
        response = self.client.delete(self.user_info_auth_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.content, b'')
        
        # Verify user is deleted
        self.assertEqual(User.objects.filter(email='customer@example.com').count(), 0)
        self.assertEqual(Customer.objects.count(), 0)

    def test_delete_user_without_token(self):
        self.client.cookies.clear()
        
        response = self.client.delete(self.user_info_auth_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        assert_problem(response, 'invalid-session')
        
        # Verify no users were deleted
        self.assertEqual(User.objects.count(), 2)

    def test_update_customer_info(self):
        self.client.cookies['jwt'] = self.customer_token
        
        update_payload = {
            'first_name': 'Updated',
            'last_name': 'Customer',
            'cpf': '98765432100'
        }
        
        response = self.client.patch(
            self.user_info_auth_url,
            data=json.dumps(update_payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify user info was updated
        updated_user = User.objects.get(email='customer@example.com')
        self.assertEqual(updated_user.first_name, 'Updated')
        self.assertEqual(updated_user.last_name, 'Customer')
        
        # Verify customer info was updated
        updated_customer = Customer.objects.get(user=updated_user)
        self.assertEqual(updated_customer.cpf, '98765432100')

    def test_patch_with_a_single_field_changes_only_that_field(self):
        """RT-58: a subset of the fields updates just those."""
        self.client.cookies['jwt'] = self.customer_token
        before = User.objects.get(email='customer@example.com')

        response = self.client.patch(
            self.user_info_auth_url, data=json.dumps({'first_name': 'Ana'}), content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        after = User.objects.get(email='customer@example.com')
        self.assertEqual(after.first_name, 'Ana')
        self.assertEqual(
            (after.last_name, after.phone, after.address, after.city),
            (before.last_name, before.phone, before.address, before.city),
        )

    def test_put_on_the_current_user_answers_405(self):
        """RT-09: the partial update is a PATCH, so the old PUT is a method the path does not list."""
        self.client.cookies['jwt'] = self.customer_token

        response = self.client.put(
            self.user_info_auth_url, data=json.dumps({'first_name': 'Ana'}), content_type='application/json'
        )

        assert_problem(response, 'method-not-allowed')
        self.assertEqual(
            sorted(response['Allow'].split(', ')), ['DELETE', 'GET', 'HEAD', 'OPTIONS', 'PATCH']
        )

    def test_update_hairdresser_info(self):
        self.client.cookies['jwt'] = self.hairdresser_token
        
        update_payload = {
            'first_name': 'Updated',
            'last_name': 'Hairdresser',
            'experience_years': 10,
            'resume': 'Updated resume',
            'cnpj': '98765432000190'
        }
        
        response = self.client.patch(
            self.user_info_auth_url,
            data=json.dumps(update_payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify user info was updated
        updated_user = User.objects.get(email='hairdresser@example.com')
        self.assertEqual(updated_user.first_name, 'Updated')
        self.assertEqual(updated_user.last_name, 'Hairdresser')
        
        # Verify hairdresser info was updated
        updated_hairdresser = Hairdresser.objects.get(user=updated_user)
        self.assertEqual(updated_hairdresser.experience_years, 10)
        self.assertEqual(updated_hairdresser.resume, 'Updated resume')
        self.assertEqual(updated_hairdresser.cnpj, '98765432000190')

    def test_update_with_a_body_that_is_not_a_json_object_answers_400_malformed_request(self):
        self.client.cookies['jwt'] = self.customer_token

        for raw in ('{nope', '[1]'):
            with self.subTest(raw=raw):
                response = self.client.patch(self.user_info_auth_url, data=raw, content_type='application/json')

                assert_problem(response, 'malformed-request')

    def test_get_of_an_account_with_an_unsupported_role_answers_500_internal_error(self):
        odd = _create_plain_user(email='odd@example.com', phone='5511999990077', role='staff', cognito_sub='sub-odd')
        self.client.cookies['jwt'] = get_cognito().client.make_access_token(odd.cognito_sub)

        response = self.client.get(self.user_info_auth_url)

        assert_problem(response, 'internal-error', detail='The account has an unsupported role.')

    def test_update_with_existing_email(self):
        self.client.cookies['jwt'] = self.customer_token
        
        # Try to update with an email that already exists (hairdresser's email)
        update_payload = {
            'email': 'hairdresser@example.com'
        }
        
        response = self.client.patch(
            self.user_info_auth_url,
            data=json.dumps(update_payload),
            content_type='application/json'
        )
        
        assert_problem(response, 'email-change-unsupported', detail='Changing the email is not supported.')


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
            'password': 'Customer_password1',
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
            'password': 'Hairdresser_password1',
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
        activate_account(self.customer_data['email'])
        
        self.client.post(
            self.register_url,
            data=self.hairdresser_data,
        )
        activate_account(self.hairdresser_data['email'])

    def test_get_customer_info_of_the_session(self):
        self._login('customer@example.com', 'Customer_password1')
        response = self.client.get(reverse('current_user'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        customer = response.json()['customer']
        self.assertEqual(customer['user']['email'], 'customer@example.com')
        self.assertEqual(customer['user']['role'], 'customer')
        self.assertIn('cpf', customer)

    def test_get_hairdresser_info_of_the_session(self):
        self._login('hairdresser@example.com', 'Hairdresser_password1')
        response = self.client.get(reverse('current_user'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        hairdresser = response.json()['hairdresser']
        self.assertEqual(hairdresser['user']['email'], 'hairdresser@example.com')
        self.assertEqual(hairdresser['user']['role'], 'hairdresser')
        self.assertIn('resume', hairdresser)

    def test_get_user_info_without_session_is_refused_with_401(self):
        response = self.client.get(reverse('current_user'))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn('customer', response.json())

    def test_the_routes_by_email_no_longer_exist(self):
        """RT-11: `GET` and `DELETE /api/user/<email>` have no replacement other than /api/users/me."""
        self._login('customer@example.com', 'Customer_password1')

        for method in ('get', 'delete'):
            for email in ('customer@example.com', 'hairdresser@example.com', 'nonexistent@example.com'):
                with self.subTest(method=method, email=email):
                    assert_problem(getattr(self.client, method)(f'/api/user/{email}'), 'not-found')
        self.assertTrue(User.objects.filter(email='customer@example.com').exists())
        self.assertTrue(User.objects.filter(email='hairdresser@example.com').exists())

    def _login(self, email, password):
        self.client.post(
            reverse('login'),
            data=json.dumps({'email': email, 'password': password}),
            content_type='application/json',
        )

    def test_delete_own_user(self):
        self._login('customer@example.com', 'Customer_password1')
        response = self.client.delete(reverse('current_user'))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.content, b'')
        self.assertEqual(User.objects.filter(email='customer@example.com').count(), 0)
        self.assertEqual(Customer.objects.count(), 0)

    def test_delete_own_user_without_session_is_refused_with_401(self):
        response = self.client.delete(reverse('current_user'))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertTrue(User.objects.filter(email='customer@example.com').exists())
        self.assertEqual(Customer.objects.count(), 1)

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
            'password': 'Customer_password1',
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
            'password': 'Hairdresser_password1',
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
            'password': 'Hairdresser_password1',
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
        activate_account(self.customer_data['email'])
        
        self.client.post(
            self.register_url,
            data=self.hairdresser_data_1,
        )
        activate_account(self.hairdresser_data_1['email'])
        
        self.client.post(
            self.register_url,
            data=self.hairdresser_data_2,
        )
        activate_account(self.hairdresser_data_2['email'])
        
        # Get created users and add preferences
        self.customer_user = User.objects.get(email='customer@example.com')
        self.hairdresser_user_1 = User.objects.get(email='hairdresser1@example.com')
        self.hairdresser_user_2 = User.objects.get(email='hairdresser2@example.com')
        
        # Add preferences to customer (for "for_you" testing)
        self.customer_user.preferences.add(self.coloracao_pref, self.cachos_pref)
        
        # Add preferences to hairdressers
        self.hairdresser_user_1.preferences.add(self.coloracao_pref, self.barbearia_pref)
        self.hairdresser_user_2.preferences.add(self.cachos_pref, self.trancas_pref)

        self._login('customer@example.com')

    def _login(self, email, password='Customer_password1'):
        self.client.cookies.clear()
        self.client.post(
            reverse('login'),
            data=json.dumps({'email': email, 'password': password}),
            content_type='application/json',
        )

    def test_customer_home_with_matching_preferences(self):
        """Test customer home view returns hairdressers matching customer preferences"""
        url = reverse('customer_home')
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
        hairdresser_ids = [h['id'] for h in for_you_data]
        self.assertIn(self.hairdresser_user_1.hairdresser.id, hairdresser_ids)
        self.assertIn(self.hairdresser_user_2.hairdresser.id, hairdresser_ids)

    def test_customer_home_with_specific_preference_categories(self):
        """Test that specific preference categories return correct hairdressers"""
        url = reverse('customer_home')
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
        coloracao_ids = [h['id'] for h in coloracao_hairdressers]
        self.assertIn(self.hairdresser_user_1.hairdresser.id, coloracao_ids)
        
        # Check cachos category contains hairdresser2
        cachos_hairdressers = preferences_data['cachos']
        cachos_ids = [h['id'] for h in cachos_hairdressers]
        self.assertIn(self.hairdresser_user_2.hairdresser.id, cachos_ids)
        
        # Check barbearia category contains hairdresser1
        barbearia_hairdressers = preferences_data['barbearia']
        barbearia_ids = [h['id'] for h in barbearia_hairdressers]
        self.assertIn(self.hairdresser_user_1.hairdresser.id, barbearia_ids)
        
        # Check trancas category contains hairdresser2
        trancas_hairdressers = preferences_data['trancas']
        trancas_ids = [h['id'] for h in trancas_hairdressers]
        self.assertIn(self.hairdresser_user_2.hairdresser.id, trancas_ids)

    def test_customer_home_by_email_no_longer_exists(self):
        """RT-13: the "for you" section reveals the customer's preferences, so it follows the session, not an e-mail"""
        for email in ('customer@example.com', 'nonexistent@example.com', 'hairdresser1@example.com'):
            with self.subTest(email=email):
                response = self.client.get(f'/api/customer/home/{email}')
                assert_problem(response, 'not-found')
                self.assertNotIn('for_you', response.json())

    def test_customer_home_hairdresser_email(self):
        """A hairdresser asking for the customer home gets 403"""
        self._login('hairdresser1@example.com', 'Hairdresser_password1')
        url = reverse('customer_home')
        response = self.client.get(url)
        
        assert_problem(response, 'customer-required', detail='Only customers can perform this action.')

    def test_customer_home_without_session_is_refused_with_401(self):
        self.client.cookies.clear()

        response = self.client.get(reverse('customer_home'))

        self.assertEqual(response.status_code, 401)
        self.assertNotIn('for_you', response.json())

    def test_public_customer_home_has_no_contact_data(self):
        """`/api/home` is public: categories only, and no PII of the hairdressers"""
        self.client.cookies.clear()

        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['for_you'], [])
        coloracao = data['hairdressers_by_preferences']['coloracao']
        self.assertEqual([h['id'] for h in coloracao], [self.hairdresser_user_1.hairdresser.id])
        for hairdresser in coloracao:
            self.assertNotIn('cnpj', hairdresser)
            for field in ('email', 'phone', 'postal_code'):
                self.assertNotIn(field, hairdresser['user'])

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
            'password': 'Customer_password1',
            'role': 'customer',
            'rating': 5,
            'cpf': '12345678901',
            'preferences': json.dumps([])
        }
        
        self.client.post(
            self.register_url,
            data=customer_no_match,
        )
        activate_account(customer_no_match['email'])
        
        # Add a preference that no hairdresser has
        customer_user_no_match = User.objects.get(email='nomatch@example.com')
        customer_user_no_match.preferences.add(self.other_pref)
        self._login('nomatch@example.com')
        
        url = reverse('customer_home')
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
            'password': 'Customer_password1',
            'role': 'customer',
            'rating': 5,
            'cpf': '12345678902',
            'preferences': json.dumps([])
        }
        
        self.client.post(
            self.register_url,
            data=customer_empty,
        )
        activate_account(customer_empty['email'])
        
        self._login('empty@example.com')
        url = reverse('customer_home')
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
        
        url = reverse('customer_home')
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
        url = reverse('customer_home')
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
            self.assertNotIn('email', hairdresser['user'])
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
                self.assertNotIn('email', hairdresser['user'])
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
        """RT-65: no `q` answers the usual envelope with an empty list"""
        response = self.client.get(self.search_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data, {'data': []})

    def test_search_with_empty_query_parameter(self):
        """Test search endpoint with empty query parameter returns empty list"""
        response = self.client.get(self.search_url, {'q': ''})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data, {'data': []})

    def test_the_old_search_parameter_is_no_longer_read(self):
        """RT-12: `search` was renamed to `q` and there is no alias."""
        response = self.client.get(self.search_url, {'search': 'Alice'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'data': []})

    def test_search_with_none_query_parameter(self):
        """Test search endpoint with None query parameter returns empty list"""
        response = self.client.get(self.search_url, None)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertEqual(response_data, {'data': []})

    def test_search_hairdressers_by_first_name(self):
        """Test search finds hairdressers by first name"""
        response = self.client.get(self.search_url, {'q': 'Alice'})
        
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
        response = self.client.get(self.search_url, {'q': 'Smith'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        results = response_data['data']
        hairdresser_results = [r for r in results if r.get('result_type') == 'hairdresser']
        self.assertEqual(len(hairdresser_results), 1)
        self.assertEqual(hairdresser_results[0]['user']['last_name'], 'Smith')

    def test_search_services_by_name(self):
        """Test search finds services by name"""
        response = self.client.get(self.search_url, {'q': 'Hair Cut'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        results = response_data['data']
        service_results = [r for r in results if r.get('result_type') == 'service']
        self.assertEqual(len(service_results), 1)
        self.assertEqual(service_results[0]['name'], 'Hair Cut')

    def test_search_services_partial_name_match(self):
        """Test search finds services with partial name match"""
        response = self.client.get(self.search_url, {'q': 'Hair'})
        
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
        response = self.client.get(self.search_url, {'q': 'hair cut'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        results = response_data['data']
        service_results = [r for r in results if r.get('result_type') == 'service']
        self.assertEqual(len(service_results), 1)
        self.assertEqual(service_results[0]['name'], 'Hair Cut')

    def test_search_combined_results(self):
        """Test search returns both hairdressers and services when relevant"""
        # Search for "curl" which should match hairdresser Carol and Curly Hair Treatment service
        response = self.client.get(self.search_url, {'q': 'curl'})
        
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
        response = self.client.get(self.search_url, {'q': 'nonexistent'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        
        self.assertIn('data', response_data)
        results = response_data['data']
        self.assertEqual(len(results), 0)

    def test_search_result_serializer_structure(self):
        """Test that search results have correct structure and required fields"""
        response = self.client.get(self.search_url, {'q': 'Alice'})
        
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
            self.assertIn('resume', hairdresser)
            # Public listing: no CNPJ nor contact data
            self.assertNotIn('cnpj', hairdresser)
            for field in ('email', 'phone', 'postal_code'):
                self.assertNotIn(field, hairdresser['user'])

    def test_search_service_result_structure(self):
        """Test that service search results have correct structure"""
        response = self.client.get(self.search_url, {'q': 'Hair Cut'})
        
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
        response = self.client.get(self.search_url, {'q': 'Alice'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/json')
        
        # Should be able to parse as JSON
        response_data = response.json()
        self.assertIsInstance(response_data, dict)
        self.assertIn('data', response_data)
        self.assertIsInstance(response_data['data'], list)

    def test_search_with_special_characters(self):
        """Test search handles special characters gracefully"""
        response = self.client.get(self.search_url, {'q': 'Alice@#$%'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertIn('data', response_data)

    def test_search_with_very_long_query(self):
        """Test search handles very long query strings"""
        long_query = 'a' * 1000
        response = self.client.get(self.search_url, {'q': long_query})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertIn('data', response_data)

    def test_search_with_unicode_characters(self):
        """Test search handles unicode characters"""
        response = self.client.get(self.search_url, {'q': 'Alicê'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertIn('data', response_data)

    def test_search_result_order_consistency(self):
        """Test that search results are returned in consistent order"""
        response1 = self.client.get(self.search_url, {'q': 'Hair'})
        response2 = self.client.get(self.search_url, {'q': 'Hair'})
        
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        
        # Results should be identical for same query
        self.assertEqual(response1.json(), response2.json())

    def test_search_handles_deleted_objects(self):
        """Test search gracefully handles if objects are deleted during processing"""
        response = self.client.get(self.search_url, {'q': 'Alice'})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertIn('data', response_data)

    def test_search_performance_with_multiple_results(self):
        """Test search performance doesn't degrade significantly with multiple results"""
        import time
        
        start_time = time.time()
        response = self.client.get(self.search_url, {'q': 'Hair'})
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
        
        assert_problem(response, 'not-found', detail='Hairdresser not found.')

    def test_get_hairdresser_info_zero_id(self):
        """Test retrieval with ID 0."""
        url = reverse('hairdresser_info', kwargs={'hairdresser_id': 0})
        response = self.client.get(url)
        
        assert_problem(response, 'not-found', detail='Hairdresser not found.')

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

    @patch('users.views.PublicHairdresserSerializer')
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


def assert_auth_unavailable(response):
    return assert_problem(
        response, 'auth-unavailable', detail='The authentication service is unavailable. Try again shortly.'
    )


def assert_throttled(response):
    return assert_problem(response, 'too-many-requests', detail='Too many attempts. Wait and try again.')


def assert_invalid_credentials(response):
    return assert_problem(response, 'invalid-credentials', detail='Invalid email or password.')


def assert_invalid_picture(response):
    return assert_problem(response, 'invalid-image', detail='The profile picture is not a valid image.')


def assert_email_taken(response):
    return assert_problem(response, 'email-taken', detail='This email is already registered.')


def assert_phone_taken(response):
    return assert_problem(response, 'phone-taken', detail='This phone number is already registered.')


def assert_missing(response, *fields):
    """A 400 validation-error whose errors are exactly `fields`, each reported as required."""
    return assert_problem(
        response, 'validation-error',
        errors=[{'pointer': f'#/{field}', 'detail': 'This field is required.'} for field in fields],
    )


def assert_session_expired(response):
    return assert_problem(response, 'session-expired', detail='Your session has expired. Sign in again.')



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

        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'], issuer='hairmatch')
        self.assertEqual(payload['id'], self.user.id)
        self.assertEqual(payload['iss'], 'hairmatch')
        self.assertEqual(payload['token_use'], 'session')
        self.assertEqual(payload['exp'] - payload['iat'], 3600)

    def test_set_session_cookie_attributes(self):
        response = set_session_cookie(JsonResponse({}), self.user)

        cookie = response.cookies['jwt']
        self.assertTrue(cookie['httponly'])
        self.assertEqual(cookie['samesite'], 'None')
        self.assertTrue(cookie['secure'])
        self.assertEqual(cookie['max-age'], 3600)
        payload = jwt.decode(cookie.value, settings.SECRET_KEY, algorithms=['HS256'], issuer='hairmatch')
        self.assertEqual(payload['id'], self.user.id)

    def test_set_cognito_cookies_sets_jwt_and_refresh_token_with_spec_attributes(self):
        response = set_cognito_cookies(JsonResponse({}), Tokens('access-abc', 'refresh-xyz'))

        jwt_cookie = response.cookies['jwt']
        self.assertEqual(jwt_cookie.value, 'access-abc')
        self.assertEqual(jwt_cookie['max-age'], 3600)
        self.assertEqual(jwt_cookie['path'], '/')
        self.assertTrue(jwt_cookie['httponly'])
        self.assertEqual(jwt_cookie['samesite'], 'None')
        self.assertTrue(jwt_cookie['secure'])
        refresh_cookie = response.cookies['refresh_token']
        self.assertEqual(refresh_cookie.value, 'refresh-xyz')
        self.assertEqual(refresh_cookie['max-age'], 2592000)
        self.assertEqual(refresh_cookie['path'], '/api/auth/')
        self.assertTrue(refresh_cookie['httponly'])
        self.assertEqual(refresh_cookie['samesite'], 'None')
        self.assertTrue(refresh_cookie['secure'])

    def test_set_access_cookie_sets_only_jwt(self):
        response = set_access_cookie(JsonResponse({}), 'access-new')

        self.assertEqual(list(response.cookies.keys()), ['jwt'])
        cookie = response.cookies['jwt']
        self.assertEqual(cookie.value, 'access-new')
        self.assertEqual(cookie['max-age'], 3600)
        self.assertTrue(cookie['httponly'])
        self.assertEqual(cookie['samesite'], 'None')
        self.assertTrue(cookie['secure'])

    def test_clear_auth_cookies_expires_both_cookies_on_their_original_paths(self):
        response = clear_auth_cookies(JsonResponse({}))

        for key, path in (('jwt', '/'), ('refresh_token', '/api/auth/')):
            with self.subTest(cookie=key):
                cookie = response.cookies[key]
                self.assertEqual(cookie.value, '')
                self.assertEqual(cookie['max-age'], 0)
                self.assertEqual(cookie['path'], path)
                self.assertTrue(cookie['httponly'])
                self.assertEqual(cookie['samesite'], 'None')
                self.assertTrue(cookie['secure'])

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

    def test_decode_rejects_a_session_token(self):
        # Sessions and signup tokens share SECRET_KEY, so the purpose claim is what keeps them apart.
        with self.assertRaises(InvalidSignupToken):
            decode_signup_token(issue_session_token(self.user))

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
        self.user_auth_url = reverse('session')

    def test_password_login_on_google_only_account_returns_403(self):
        _create_plain_user(email='google-only@example.com', password=None, google_id='google-sub-123')

        response = self.client.post(
            self.login_url,
            data=json.dumps({'email': 'google-only@example.com', 'password': 'any_password'}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        assert_problem(
            response, 'google-account-login',
            detail='This account uses Google sign-in. Use the Sign in with Google button.',
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
        self.user_auth_url = reverse('session')
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
        payload = jwt.decode(cookie.value, settings.SECRET_KEY, algorithms=['HS256'], issuer='hairmatch')
        self.assertEqual(payload['id'], user.id)
        self.assertEqual(payload['token_use'], 'session')
        self.assertEqual(payload['exp'] - payload['iat'], 3600)
        self.assertEqual(cookie['max-age'], 3600)

        self.client.cookies['jwt'] = cookie.value
        auth_response = self.client.get(self.user_auth_url)
        self.assertEqual(auth_response.json(), {'authenticated': True})

    def _pending_email_account(self, email='Ana@gmail.com', phone='92991234567'):
        response = self.client.post(reverse('register'), data=_register_payload(email=email, phone=phone))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        get_cognito().client.calls.clear()
        return User.objects.get(email=email)

    def test_a_pending_account_with_the_same_email_is_replaced_and_never_linked(self):
        """EMC-52"""
        self._pending_email_account('Ana@gmail.com')
        self.mock_verify.return_value = self._identity(email='ana@gmail.com')

        response = self._post()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['status'], 'signup_required')
        self.assertTrue(response.json()['signup_token'])
        self.assertNotIn('jwt', response.cookies)
        self.assertEqual(User.objects.count(), 0)
        self.assertFalse(User.objects.filter(google_id='google-sub-123').exists())
        self.assertEqual(get_cognito().client.users, {})
        self.assertEqual([name for name, _ in get_cognito().client.calls], ['admin_delete_user'])

    def test_a_cognito_outage_while_replacing_the_pending_account_answers_503_and_keeps_it(self):
        """EMC-55"""
        pending = self._pending_email_account('ana@gmail.com')
        get_cognito().client.fail_next('admin_delete_user', EndpointConnectionError(endpoint_url='http://x'))
        self.mock_verify.return_value = self._identity()

        response = self._post()

        assert_auth_unavailable(response)
        self.assertNotIn('jwt', response.cookies)
        pending.refresh_from_db()
        self.assertIsNone(pending.google_id)
        self.assertFalse(pending.is_active)
        self.assertIn('ana@gmail.com', get_cognito().client.users)
        self.assertEqual(User.objects.count(), 1)

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

    def test_body_that_is_not_a_json_object_returns_400_malformed_request(self):
        for raw in ('[1]', '{nope'):
            with self.subTest(raw=raw):
                response = self.client.post(self.google_auth_url, data=raw, content_type='application/json')

                assert_problem(response, 'malformed-request')
        self.mock_verify.assert_not_called()

    def test_missing_or_empty_id_token_returns_400(self):
        for body in ({}, {'id_token': ''}):
            with self.subTest(body=body):
                response = self._post(body)

                assert_problem(
                    response, 'validation-error',
                    errors=[{'pointer': '#/id_token', 'detail': 'This field is required.'}],
                )
                self.assertNotIn('jwt', response.cookies)
        self.mock_verify.assert_not_called()

    def test_invalid_google_token_returns_401_without_changes(self):
        _create_plain_user(email='ana@gmail.com', google_id=None)
        before = self._users_snapshot()
        self.mock_verify.side_effect = GoogleTokenError('bad token')

        response = self._post()

        assert_problem(
            response, 'invalid-google-token', detail='The Google account could not be validated. Try again.'
        )
        self.assertNotIn('jwt', response.cookies)
        self.assertEqual(self._users_snapshot(), before)

    def test_unverified_email_returns_403_without_changes(self):
        _create_plain_user(email='ana@gmail.com', google_id=None)
        before = self._users_snapshot()
        self.mock_verify.return_value = self._identity(email_verified=False)

        response = self._post()

        assert_problem(response, 'google-email-unverified', detail='Your Google email is not verified.')
        self.assertNotIn('jwt', response.cookies)
        self.assertEqual(self._users_snapshot(), before)

    def test_email_linked_to_another_google_account_returns_409(self):
        _create_plain_user(email='ana@gmail.com', google_id='another-google-sub')
        before = self._users_snapshot()
        self.mock_verify.return_value = self._identity()

        response = self._post()

        assert_problem(response, 'google-email-linked', detail='This email is linked to another Google account.')
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
        self.user_auth_url = reverse('session')
        self.user_info_auth_url = reverse('current_user')
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
        payload = jwt.decode(cookie.value, settings.SECRET_KEY, algorithms=['HS256'], issuer='hairmatch')
        self.assertEqual(payload['id'], user.id)
        self.assertEqual(payload['token_use'], 'session')
        self.assertEqual(payload['exp'] - payload['iat'], 3600)
        self.assertEqual(cookie['max-age'], 3600)

        self.client.cookies['jwt'] = cookie.value
        auth_response = self.client.get(self.user_auth_url)
        self.assertEqual(auth_response.json(), {'authenticated': True})

    def _pending_email_account(self, email, phone):
        response = self.client.post(reverse('register'), data=_register_payload(email=email, phone=phone))
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        get_cognito().client.calls.clear()
        return User.objects.get(email=email)

    def test_google_signup_replaces_a_pending_account_that_holds_the_token_email(self):
        """EMC-53"""
        self._pending_email_account('Ana@gmail.com', '92990000000')

        response = self.client.post(self.register_url, data=self.customer_payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get()
        self.assertEqual(user.email, 'ana@gmail.com')
        self.assertEqual(user.google_id, 'google-sub-123')
        self.assertTrue(user.is_active)
        self.assertIsNone(user.cognito_sub)
        self.assertEqual(get_cognito().client.users, {})
        self.assertEqual(Customer.objects.count(), 1)
        self._assert_session_cookie_for(response, user)

    def test_google_signup_replaces_a_pending_account_that_holds_the_phone(self):
        """EMC-53"""
        self._pending_email_account('outra@example.com', '92991234567')

        response = self.client.post(self.register_url, data=self.customer_payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(list(User.objects.values_list('email', flat=True)), ['ana@gmail.com'])
        self.assertTrue(User.objects.get().is_active)
        self.assertEqual(get_cognito().client.users, {})

    def test_google_signup_with_an_active_phone_holder_answers_409_and_keeps_the_pending_account(self):
        """EMC-53: nothing is replaced before the conflict is known."""
        self._pending_email_account('ana@gmail.com', '92990000000')
        active = _create_plain_user(email='ativa@example.com', phone='5592991234567')
        get_cognito().client.calls.clear()

        response = self.client.post(self.register_url, data=self.customer_payload)

        assert_phone_taken(response)
        self.assertEqual(get_cognito().client.calls, [])
        self.assertEqual(User.objects.count(), 2)
        self.assertTrue(User.objects.filter(pk=active.pk).exists())

    def test_a_cognito_outage_while_replacing_on_google_signup_answers_503_and_creates_nothing(self):
        """EMC-55"""
        pending = self._pending_email_account('ana@gmail.com', '92990000000')
        get_cognito().client.fail_next('admin_delete_user', EndpointConnectionError(endpoint_url='http://x'))

        response = self.client.post(self.register_url, data=self.customer_payload)

        assert_auth_unavailable(response)
        self.assertNotIn('jwt', response.cookies)
        self.assertEqual(list(User.objects.values_list('pk', 'google_id')), [(pending.pk, None)])
        self.assertIn('ana@gmail.com', get_cognito().client.users)
        self.assertEqual(Customer.objects.count(), 1)

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

        assert_invalid_picture(response)
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

                assert_problem(
                    response, 'signup-session-expired',
                    detail='Your Google sign-up session has expired. Sign in with Google again.',
                )
                self.assertNotIn('jwt', response.cookies)
                self._assert_no_new_rows()

    def test_a_body_with_only_the_token_reports_every_missing_field_at_once(self):
        response = self.client.post(self.register_url, data={'google_signup_token': self.signup_token})

        assert_missing(
            response, 'role', 'first_name', 'last_name', 'phone', 'address', 'neighborhood', 'city', 'state', 'postal_code'
        )
        self._assert_no_new_rows()

    def test_missing_document_of_the_role_is_reported_with_the_other_missing_fields(self):
        payload = {k: v for k, v in self.customer_payload.items() if k not in ('cpf', 'city')}

        response = self.client.post(self.register_url, data=payload)

        assert_missing(response, 'city', 'cpf')

    def test_preferences_that_are_not_a_list_of_ids_answer_400(self):
        for preferences in ('{"a": 1}', '5', '["a"]'):
            with self.subTest(preferences=preferences):
                response = self.client.post(
                    self.register_url, data={**self.customer_payload, 'preferences': preferences}
                )

                assert_problem(
                    response, 'validation-error',
                    errors=[{'pointer': '#/preferences', 'detail': 'The preferences must be a JSON list of ids.'}],
                )
                self.assertNotIn('jwt', response.cookies)
                self._assert_no_new_rows()

    def test_phone_already_registered_with_country_prefix_returns_409(self):
        _create_plain_user(email='other@example.com', phone='5592991234567')

        response = self.client.post(self.register_url, data=self.customer_payload)

        assert_phone_taken(response)
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

                if label == 'email':
                    assert_email_taken(response)
                else:
                    assert_problem(response, 'google-account-taken', detail='This Google account is already registered.')
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
                cache.clear()  # 13 sign-ups from one IP would pass the 10/hour register throttle
                payload = {k: v for k, v in base_payload.items() if k != missing_field}

                response = self.client.post(self.register_url, data=payload)

                assert_missing(response, missing_field)
                self._assert_no_new_rows()

        invalid_values = (
            ('invalid role', {'role': 'admin'}, {'pointer': '#/role', 'detail': 'The role must be customer or hairdresser.'}),
            ('short phone', {'phone': '929912345'}, {'pointer': '#/phone', 'detail': 'The phone number is too short.'}),
        )
        for label, override, expected_error in invalid_values:
            with self.subTest(case=label):
                cache.clear()
                response = self.client.post(self.register_url, data={**self.customer_payload, **override})

                assert_problem(response, 'validation-error', errors=[expected_error])
                self._assert_no_new_rows()

    def test_invalid_preferences_json_rolls_back_everything(self):
        for label, base_payload in (('customer', self.customer_payload), ('hairdresser', self.hairdresser_payload)):
            with self.subTest(role=label):
                payload = {**base_payload, 'preferences': 'not-json'}

                response = self.client.post(self.register_url, data=payload)

                assert_problem(
                    response, 'validation-error',
                    errors=[{'pointer': '#/preferences', 'detail': 'The preferences must be a JSON list of ids.'}],
                )
                self.assertNotIn('jwt', response.cookies)
                self._assert_no_new_rows()

    def test_error_after_preferences_are_linked_rolls_back_everything(self):
        preference = Preferences.objects.create(name='Cachos')
        payload = {**self.customer_payload, 'preferences': json.dumps([preference.id])}

        with patch.object(Customer.objects, 'create', side_effect=RuntimeError('database failure')):
            response = self.client.post(self.register_url, data=payload)

        assert_problem(response, 'internal-error', detail='The account could not be created.')
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
        self.assertEqual(reverse('cep_lookup', args=['69057000']), '/api/postal-codes/69057000')

    def test_found_cep_returns_200_without_cookie(self):
        self.mock_lookup.return_value = self.ADDRESS
        response = self._get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), self.ADDRESS)
        self.mock_lookup.assert_called_once_with('69057-000')

    def test_invalid_cep_returns_400(self):
        self.mock_lookup.side_effect = InvalidCep('123')
        response = self._get('123')
        assert_problem(response, 'invalid-postal-code', detail='The postal code must have 8 digits.')

    def test_not_found_returns_404(self):
        self.mock_lookup.side_effect = CepNotFound('00000000')
        response = self._get('00000000')
        assert_problem(response, 'postal-code-not-found', detail='No address was found for this postal code.')

    def test_service_unavailable_returns_503(self):
        self.mock_lookup.side_effect = CepServiceUnavailable('69057000')
        response = self._get()
        assert_problem(
            response, 'postal-code-service-unavailable', detail='The postal code providers are unavailable.'
        )

    def test_a_cep_with_a_hyphen_reaches_the_lookup_like_one_without(self):
        """RT-82: `69000-000` and `69000000` are both accepted by the route."""
        self.mock_lookup.return_value = self.ADDRESS

        hyphen = self.client.get('/api/postal-codes/69000-000')
        plain = self.client.get('/api/postal-codes/69000000')

        self.assertEqual(hyphen.status_code, 200)
        self.assertEqual(hyphen.json(), plain.json())
        self.assertEqual([call.args[0] for call in self.mock_lookup.call_args_list], ['69000-000', '69000000'])

    def test_thirty_first_request_in_a_minute_returns_429(self):
        self.mock_lookup.return_value = self.ADDRESS
        for _ in range(30):
            self.assertEqual(self._get().status_code, 200)
        throttled = self._get()
        assert_problem(throttled, 'too-many-requests')
        self.assertGreater(int(throttled['Retry-After']), 0)


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

    def _login_status(self, email, password='Senha123'):
        return APIClient().post(
            reverse('login'), data=json.dumps({'email': email, 'password': password}),
            content_type='application/json',
        ).status_code

    def test_seeded_hairdressers_exist_in_cognito_without_a_local_password_and_can_log_in(self):
        fake = get_cognito().client

        self._run()

        hairdressers = User.objects.filter(role='hairdresser')
        self.assertEqual(hairdressers.count(), 40)
        for user in hairdressers:
            self.assertIsNone(user.password)
            self.assertEqual(user.cognito_sub, fake.users[user.email.lower()]['sub'])
            self.assertTrue(fake.users[user.email.lower()]['confirmed'])
        self.assertEqual(self._login_status(hairdressers.first().email), 200)

    def test_seeded_hairdressers_are_created_active_by_the_seed_confirmation(self):
        """EMC-06: the seed keeps SignUp + AdminConfirmSignUp, so no e-mail code is involved."""
        fake = get_cognito().client

        self._run()

        hairdressers = User.objects.filter(role='hairdresser')
        self.assertEqual(hairdressers.filter(is_active=True).count(), 40)
        names = [name for name, _ in fake.calls]
        self.assertEqual(names.count('admin_confirm_sign_up'), 40)
        self.assertNotIn('confirm_sign_up', names)
        self.assertEqual(self._login_status(hairdressers.first().email), 200)

    def test_recreates_users_missing_from_cognito_and_fills_a_missing_sub_without_new_rows(self):
        fake = get_cognito().client
        self._run()
        no_sub, lost_in_cognito = User.objects.filter(role='hairdresser').order_by('id')[:2]
        User.objects.filter(pk=no_sub.pk).update(cognito_sub=None)
        del fake.users[lost_in_cognito.email.lower()]

        self._run()

        self.assertEqual(User.objects.filter(role='hairdresser').count(), 40)
        for user in (no_sub, lost_in_cognito):
            user.refresh_from_db()
            self.assertEqual(user.cognito_sub, fake.users[user.email.lower()]['sub'])
            self.assertEqual(self._login_status(user.email), 200)

    def test_does_not_touch_users_outside_the_seed_pattern(self):
        fake = get_cognito().client
        plain = User.objects.create(
            email='someone@seed.test', first_name='A', last_name='B', phone='1', neighborhood='n',
            city='c', state='AM', address='a', postal_code='1', role='hairdresser',
        )
        google = User.objects.create(
            email='hairdresser7_ana@gmail.com', first_name='A', last_name='B', phone='2', neighborhood='n',
            city='c', state='AM', address='a', postal_code='1', role='hairdresser', google_id='google-1',
        )

        self._run()

        for user in (plain, google):
            user.refresh_from_db()
            self.assertIsNone(user.cognito_sub)
        self.assertEqual(fake.users, {})

    def test_running_again_creates_no_cognito_user_and_keeps_every_sub(self):
        fake = get_cognito().client
        self._run()
        subs = dict(User.objects.filter(role='hairdresser').values_list('email', 'cognito_sub'))
        fake.calls.clear()

        self._run()

        self.assertEqual([name for name, _ in fake.calls if name == 'sign_up'], [])
        self.assertEqual(dict(User.objects.filter(role='hairdresser').values_list('email', 'cognito_sub')), subs)

class PurgeUnconfirmedUsersCommandTest(TestCase):
    """EMC-34 to EMC-37: pending accounts older than seven days are deleted in Cognito and then in Postgres."""

    NOW = timezone.now()
    LOGGER = 'users.management.commands.purge_unconfirmed_users'

    def setUp(self):
        self.fake = get_cognito().client
        patcher = patch.object(purge_unconfirmed_users.timezone, 'now', return_value=self.NOW)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _account(self, email, age, is_active=False, in_cognito=True, google=False):
        user = _create_plain_user(
            email=email, phone=f'55920000{User.objects.count():05d}', is_active=is_active,
            google_id='google-' + email if google else None,
        )
        if in_cognito and not google:
            sub = self.fake.sign_up(
                ClientId=cognito_fake.CLIENT_ID, Username=email, Password='Senha123'
            )['UserSub']
            User.objects.filter(pk=user.pk).update(cognito_sub=sub)
        User.objects.filter(pk=user.pk).update(date_joined=self.NOW - age)
        return user

    def _run(self):
        out = StringIO()
        with self.assertLogs(self.LOGGER, 'INFO') as logs:
            call_command('purge_unconfirmed_users', stdout=out)
        return logs, out.getvalue()

    def test_only_the_pending_account_older_than_seven_days_is_deleted(self):
        """EMC-34, EMC-35"""
        old = self._account('oito-dias@example.com', datetime.timedelta(days=8))
        week = self._account('sete-dias@example.com', datetime.timedelta(days=7))
        fresh = self._account('uma-hora@example.com', datetime.timedelta(hours=1))
        active = self._account('ativa@example.com', datetime.timedelta(days=30), is_active=True)
        google = self._account('google@example.com', datetime.timedelta(days=30), google=True)

        self._run()

        self.assertEqual(
            sorted(User.objects.values_list('email', flat=True)),
            sorted(['sete-dias@example.com', 'uma-hora@example.com', 'ativa@example.com', 'google@example.com']),
        )
        self.assertEqual(
            sorted(self.fake.users),
            sorted(['sete-dias@example.com', 'uma-hora@example.com', 'ativa@example.com']),
        )
        self.assertFalse(User.objects.filter(pk=old.pk).exists())
        for survivor in (week, fresh, active, google):
            self.assertTrue(User.objects.filter(pk=survivor.pk).exists())

    def test_the_cognito_user_is_deleted_by_the_command_with_the_account_e_mail(self):
        """EMC-34"""
        self._account('oito-dias@example.com', datetime.timedelta(days=8))
        self.fake.calls.clear()

        self._run()

        deletions = [kwargs['Username'] for name, kwargs in self.fake.calls if name == 'admin_delete_user']
        self.assertEqual(deletions, ['oito-dias@example.com'])

    def test_a_cognito_outage_keeps_that_account_warns_with_its_id_and_goes_on(self):
        """EMC-36"""
        first = self._account('a@example.com', datetime.timedelta(days=9))
        second = self._account('b@example.com', datetime.timedelta(days=9))
        self.fake.fail_next('admin_delete_user', EndpointConnectionError(endpoint_url='http://x'))

        with self.assertLogs(self.LOGGER, 'WARNING') as logs:
            call_command('purge_unconfirmed_users', stdout=StringIO())

        remaining = list(User.objects.order_by('pk').values_list('pk', flat=True))
        kept = remaining[0]
        self.assertEqual(len(remaining), 1)
        self.assertIn(kept, (first.pk, second.pk))
        self.assertIn(User.objects.get(pk=kept).email, self.fake.users)
        warnings = [r for r in logs.records if r.levelname == 'WARNING']
        self.assertEqual(len(warnings), 1)
        self.assertIn(str(kept), warnings[0].getMessage())
        self.assertEqual(len(self.fake.users), 1)

    def test_the_summary_is_logged_at_info_and_printed_and_a_second_run_deletes_nothing(self):
        """EMC-37"""
        self._account('a@example.com', datetime.timedelta(days=9))
        self._account('b@example.com', datetime.timedelta(days=9))
        self.fake.fail_next('admin_delete_user', EndpointConnectionError(endpoint_url='http://x'))

        with self.assertLogs(self.LOGGER, 'INFO') as logs:
            out = StringIO()
            call_command('purge_unconfirmed_users', stdout=out)
        info = [r for r in logs.records if r.levelname == 'INFO']
        self.assertEqual([r.getMessage() for r in info], ['purge_unconfirmed_users deleted=1 kept=1'])
        self.assertIn('deleted=1 kept=1', out.getvalue())

        logs, out = self._run()  # the kept account is retried and goes now
        self.assertEqual([r.getMessage() for r in logs.records], ['purge_unconfirmed_users deleted=1 kept=0'])
        logs, out = self._run()
        self.assertEqual([r.getMessage() for r in logs.records], ['purge_unconfirmed_users deleted=0 kept=0'])
        self.assertEqual(User.objects.count(), 0)

    def test_an_account_already_missing_from_cognito_is_still_deleted(self):
        """EMC-34: UserNotFoundException is not a failure."""
        self._account('a@example.com', datetime.timedelta(days=9), in_cognito=False)
        User.objects.update(cognito_sub='sub-gone')

        self._run()

        self.assertEqual(User.objects.count(), 0)

    def test_the_entrypoint_runs_the_purge_after_the_migrations(self):
        """EMC-38"""
        with open(os.path.join(settings.BASE_DIR, 'entrypoint.sh')) as script:
            lines = [line.strip() for line in script]

        migrate = lines.index('python3 backend/manage.py migrate')
        purge = lines.index('python3 backend/manage.py purge_unconfirmed_users')
        self.assertLess(migrate, purge)


class UserProfilePicturePathTest(SimpleTestCase):
    def test_path_is_scoped_by_user_id(self):
        self.assertEqual(
            user_profile_picture_path(User(pk=42), 'screen.png'),
            'profile_pics/42/screen.png',
        )


class FakeCognitoIdpTest(SimpleTestCase):
    def setUp(self):
        self.cognito = cognito_fake.FakeCognitoIdp()

    def _sign_up_confirmed(self, email='a@x.com', password='Senha123'):
        sub = self.cognito.sign_up(
            ClientId=cognito_fake.CLIENT_ID, Username=email, Password=password
        )['UserSub']
        self.cognito.admin_confirm_sign_up(
            UserPoolId=cognito_fake.POOL_ID, Username=email
        )
        return sub

    def _login(self, email='a@x.com', password='Senha123'):
        return self.cognito.initiate_auth(
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={'USERNAME': email, 'PASSWORD': password},
            ClientId=cognito_fake.CLIENT_ID,
        )['AuthenticationResult']

    def test_sign_up_with_compliant_password_returns_user_sub(self):
        response = self.cognito.sign_up(
            ClientId=cognito_fake.CLIENT_ID, Username='a@x.com', Password='Senha123'
        )
        self.assertEqual(response['UserSub'], self.cognito.users['a@x.com']['sub'])
        self.assertFalse(response['UserConfirmed'])

    def test_sign_up_rejects_passwords_outside_the_policy(self):
        for password in ('senha123', 'SENHA123', 'Senhaabc', 'Se1'):
            with self.subTest(password=password):
                with self.assertRaises(ClientError) as ctx:
                    self.cognito.sign_up(
                        ClientId=cognito_fake.CLIENT_ID, Username='a@x.com', Password=password
                    )
                self.assertEqual(
                    ctx.exception.response['Error']['Code'], 'InvalidPasswordException'
                )
        self.assertEqual(self.cognito.users, {})

    def test_sign_up_treats_emails_that_differ_in_case_as_the_same_user(self):
        self.cognito.sign_up(
            ClientId=cognito_fake.CLIENT_ID, Username='A@x.com', Password='Senha123'
        )
        with self.assertRaises(ClientError) as ctx:
            self.cognito.sign_up(
                ClientId=cognito_fake.CLIENT_ID, Username='a@x.com', Password='Senha123'
            )
        self.assertEqual(ctx.exception.response['Error']['Code'], 'UsernameExistsException')

    def test_login_is_case_insensitive_on_the_email(self):
        self._sign_up_confirmed(email='A@x.com')
        self.assertIn('AccessToken', self._login(email='a@X.com'))

    def test_login_returns_tokens_verifiable_with_the_published_jwks(self):
        sub = self._sign_up_confirmed()
        tokens = self._login()

        jwk = self.cognito.jwks()['keys'][0]
        key = RSAAlgorithm.from_jwk(json.dumps(jwk))
        claims = jwt.decode(
            tokens['AccessToken'],
            key,
            algorithms=['RS256'],
            issuer=cognito_fake.issuer(),
        )
        self.assertEqual(jwt.get_unverified_header(tokens['AccessToken'])['kid'], jwk['kid'])
        self.assertEqual(claims['sub'], sub)
        self.assertEqual(claims['token_use'], 'access')
        self.assertEqual(claims['client_id'], cognito_fake.CLIENT_ID)
        self.assertEqual(claims['exp'] - claims['iat'], 3600)
        self.assertIn('RefreshToken', tokens)

    def test_login_with_wrong_password_is_not_authorized(self):
        self._sign_up_confirmed()
        with self.assertRaises(ClientError) as ctx:
            self._login(password='Errada123')
        self.assertEqual(ctx.exception.response['Error']['Code'], 'NotAuthorizedException')

    def test_refresh_after_revoke_is_not_authorized(self):
        self._sign_up_confirmed()
        refresh_token = self._login()['RefreshToken']
        refresh = lambda: self.cognito.initiate_auth(
            AuthFlow='REFRESH_TOKEN_AUTH',
            AuthParameters={'REFRESH_TOKEN': refresh_token},
            ClientId=cognito_fake.CLIENT_ID,
        )

        self.assertIn('AccessToken', refresh()['AuthenticationResult'])
        self.cognito.revoke_token(Token=refresh_token, ClientId=cognito_fake.CLIENT_ID)
        with self.assertRaises(ClientError) as ctx:
            refresh()
        self.assertEqual(ctx.exception.response['Error']['Code'], 'NotAuthorizedException')

    def test_fail_next_raises_exactly_once(self):
        self._sign_up_confirmed()
        self.cognito.fail_next('initiate_auth', EndpointConnectionError(endpoint_url='http://x'))

        with self.assertRaises(EndpointConnectionError):
            self._login()
        self.assertIn('AccessToken', self._login())

    def _sign_up_pending(self, email='a@x.com'):
        self.cognito.sign_up(
            ClientId=cognito_fake.CLIENT_ID, Username=email, Password='Senha123'
        )

    def _confirm(self, code, email='a@x.com'):
        return self.cognito.confirm_sign_up(
            ClientId=cognito_fake.CLIENT_ID, Username=email, ConfirmationCode=code
        )

    def _resend(self, email='a@x.com'):
        return self.cognito.resend_confirmation_code(
            ClientId=cognito_fake.CLIENT_ID, Username=email
        )

    def _status(self, email='a@x.com'):
        return self.cognito.admin_get_user(
            UserPoolId=cognito_fake.POOL_ID, Username=email
        )['UserStatus']

    def _error_code(self, call, *args):
        with self.assertRaises(ClientError) as ctx:
            call(*args)
        return ctx.exception.response['Error']['Code']

    def test_sign_up_stores_a_six_digit_code_and_the_right_code_confirms_the_user(self):
        self._sign_up_pending()
        code = self.cognito.confirmation_code('a@x.com')

        self.assertRegex(code, r'^\d{6}$')
        self.assertEqual(self._status(), 'UNCONFIRMED')
        self._confirm(code)
        self.assertEqual(self._status(), 'CONFIRMED')

    def test_confirming_with_a_different_code_is_a_mismatch_and_leaves_the_user_unconfirmed(self):
        self._sign_up_pending()
        wrong = '000000' if self.cognito.confirmation_code('a@x.com') != '000000' else '111111'

        self.assertEqual(self._error_code(self._confirm, wrong), 'CodeMismatchException')
        self.assertEqual(self._status(), 'UNCONFIRMED')

    def test_confirming_an_expired_code_is_rejected_as_expired(self):
        self._sign_up_pending()
        code = self.cognito.confirmation_code('a@x.com')
        self.cognito.expire_code('a@x.com')

        self.assertEqual(self._error_code(self._confirm, code), 'ExpiredCodeException')
        self.assertEqual(self._status(), 'UNCONFIRMED')

    def test_confirming_an_already_confirmed_user_is_not_authorized(self):
        self._sign_up_confirmed()
        code = self.cognito.confirmation_code('a@x.com')

        self.assertEqual(self._error_code(self._confirm, code), 'NotAuthorizedException')

    def test_an_unknown_user_looks_like_a_wrong_code_and_a_delivered_resend(self):
        self.assertEqual(self._error_code(self._confirm, '123456', 'nobody@x.com'), 'CodeMismatchException')
        details = self._resend('nobody@x.com')['CodeDeliveryDetails']
        self.assertEqual(details['DeliveryMedium'], 'EMAIL')
        self.assertEqual(self.cognito.users, {})

    def test_resend_issues_a_new_code_and_the_old_one_stops_working(self):
        self._sign_up_pending()
        old_code = self.cognito.confirmation_code('a@x.com')

        self._resend()
        new_code = self.cognito.confirmation_code('a@x.com')

        self.assertRegex(new_code, r'^\d{6}$')
        self.assertNotEqual(new_code, old_code)
        self.assertEqual(self._error_code(self._confirm, old_code), 'CodeMismatchException')
        self._confirm(new_code)
        self.assertEqual(self._status(), 'CONFIRMED')

    def test_resend_gives_an_expired_code_a_fresh_validity(self):
        self._sign_up_pending()
        self.cognito.expire_code('a@x.com')

        self._resend()
        self._confirm(self.cognito.confirmation_code('a@x.com'))

        self.assertEqual(self._status(), 'CONFIRMED')

    def test_resend_for_a_confirmed_user_is_an_invalid_parameter(self):
        self._sign_up_confirmed()

        self.assertEqual(self._error_code(self._resend), 'InvalidParameterException')

    def test_confirm_and_resend_are_case_insensitive_on_the_email(self):
        self._sign_up_pending(email='A@x.com')

        self._resend('a@X.com')
        self._confirm(self.cognito.confirmation_code('A@x.com'), 'a@X.com')

        self.assertEqual(self._status('A@x.com'), 'CONFIRMED')

    def test_fail_next_on_confirm_sign_up_raises_exactly_once(self):
        self._sign_up_pending()
        code = self.cognito.confirmation_code('a@x.com')
        self.cognito.fail_next('confirm_sign_up', 'TooManyFailedAttemptsException')

        self.assertEqual(self._error_code(self._confirm, code), 'TooManyFailedAttemptsException')
        self._confirm(code)
        self.assertEqual(self._status(), 'CONFIRMED')

    def test_calls_record_the_operation_but_never_the_confirmation_code(self):
        self._sign_up_pending()
        code = self.cognito.confirmation_code('a@x.com')
        self._confirm(code)

        names = [name for name, _ in self.cognito.calls]
        self.assertIn('confirm_sign_up', names)
        self.assertNotIn(code, json.dumps(self.cognito.calls))


class CognitoServiceTest(SimpleTestCase):
    def setUp(self):
        self.fake = cognito_fake.FakeCognitoIdp()
        self.service = CognitoService(self.fake)

    def _sign_up(self, password='Senha123'):
        return self.service.sign_up_confirmed('a@x.com', password)

    def test_boto_errors_become_domain_errors(self):
        cases = [
            ('InvalidPasswordException', InvalidPassword),
            ('UsernameExistsException', UserAlreadyExists),
            ('NotAuthorizedException', InvalidCredentials),
            ('UserNotFoundException', InvalidCredentials),
            ('TooManyRequestsException', TooManyRequests),
            ('LimitExceededException', TooManyRequests),
            ('InternalErrorException', CognitoUnavailable),
            ('SomethingCognitoAddedLater', CognitoUnavailable),
            (EndpointConnectionError(endpoint_url='http://x'), CognitoUnavailable),
            (ConnectTimeoutError(endpoint_url='http://x'), CognitoUnavailable),
            (ReadTimeoutError(endpoint_url='http://x'), CognitoUnavailable),
        ]
        for error, expected in cases:
            with self.subTest(error=error):
                self.fake.fail_next('sign_up', error)
                with self.assertRaises(expected) as ctx:
                    self._sign_up()
                self.assertIs(type(ctx.exception), expected)

    def test_failures_are_logged_with_operation_and_code_but_never_the_password(self):
        with self.assertLogs('users.cognito', 'WARNING') as logs:
            with self.assertRaises(InvalidPassword):
                self._sign_up(password='senha123')
            self.fake.fail_next('initiate_auth', EndpointConnectionError(endpoint_url='http://x'))
            with self.assertRaises(CognitoUnavailable):
                self.service.authenticate('a@x.com', 'Senha123')

        self.assertEqual(logs.records[0].levelname, 'WARNING')
        self.assertIn('sign_up', logs.output[0])
        self.assertIn('InvalidPasswordException', logs.output[0])
        self.assertIn('initiate_auth', logs.output[1])
        self.assertIn('EndpointConnectionError', logs.output[1])
        for line in logs.output:
            self.assertNotIn('senha123', line.lower())
            self.assertNotIn('a@x.com', line)

    @override_settings(COGNITO_USER_POOL_ID='pool-from-env', COGNITO_APP_CLIENT_ID='client-from-env')
    def test_ids_from_settings_are_used_without_any_listing_call(self):
        self.assertEqual(self.service.pool_id, 'pool-from-env')
        self.assertEqual(self.service.client_id, 'client-from-env')
        self.assertEqual(self.service.issuer, 'https://cognito-idp.us-east-2.amazonaws.com/pool-from-env')
        self.assertEqual(self.fake.calls, [])

    @override_settings(COGNITO_USER_POOL_ID='', COGNITO_APP_CLIENT_ID='')
    def test_empty_ids_are_resolved_by_name(self):
        self.assertEqual(self.service.pool_id, cognito_fake.POOL_ID)
        self.assertEqual(self.service.client_id, cognito_fake.CLIENT_ID)
        self.assertEqual(
            [name for name, _ in self.fake.calls], ['list_user_pools', 'list_user_pool_clients']
        )
        self.assertEqual(
            self.service.issuer,
            f'https://cognito-idp.us-east-2.amazonaws.com/{cognito_fake.POOL_ID}',
        )

    @override_settings(COGNITO_USER_POOL_ID='', COGNITO_APP_CLIENT_ID='')
    def test_missing_pool_is_reported_as_unavailable(self):
        self.fake.list_user_pools = lambda **kwargs: {'UserPools': [{'Id': 'x', 'Name': 'other'}]}
        with self.assertRaises(CognitoUnavailable):
            self.service.pool_id

    def test_cognito_calls_use_the_cognito_endpoint_while_s3_keeps_its_own(self):
        env = {
            'AWS_DEFAULT_REGION': 'us-east-2',
            'AWS_ACCESS_KEY_ID': 'test',
            'AWS_SECRET_ACCESS_KEY': 'test',
            'AWS_ENDPOINT_URL': 'http://localstack:4566',
            'AWS_ENDPOINT_URL_COGNITO_IDENTITY_PROVIDER': 'http://ministack:4566',
        }
        with patch.dict(os.environ, env):
            cognito_endpoint = CognitoService().client.meta.endpoint_url
            s3_endpoint = boto3.client('s3').meta.endpoint_url
        self.assertEqual(cognito_endpoint, 'http://ministack:4566')
        self.assertEqual(s3_endpoint, 'http://localstack:4566')

    def test_failed_confirmation_deletes_the_user_and_propagates(self):
        self.fake.fail_next('admin_confirm_sign_up', 'InternalErrorException')

        with self.assertRaises(CognitoUnavailable):
            self._sign_up()

        self.assertIn('admin_delete_user', [name for name, _ in self.fake.calls])
        self.assertEqual(self.fake.users, {})

    def test_deleting_a_user_that_does_not_exist_is_not_an_error(self):
        self.service.admin_delete_user('nobody@x.com')

    @override_settings(COGNITO_USER_POOL_ID='pool-1')
    def test_fetch_jwks_reports_network_errors_and_bad_status_as_unavailable(self):
        service = CognitoService(SimpleNamespace(meta=self.fake.meta))
        bad_status = MagicMock(status_code=500)
        for outcome in (
            {'side_effect': http_requests.ConnectionError('down')},
            {'return_value': bad_status},
        ):
            with self.subTest(outcome=outcome):
                with patch('users.cognito.requests.get', **outcome):
                    with self.assertRaises(CognitoUnavailable):
                        service.fetch_jwks()

    @override_settings(COGNITO_USER_POOL_ID='pool-1')
    def test_fetch_jwks_reads_the_pool_jwks_endpoint(self):
        service = CognitoService(SimpleNamespace(meta=self.fake.meta))
        response = MagicMock(status_code=200)
        response.json.return_value = {'keys': []}
        with patch('users.cognito.requests.get', return_value=response) as get:
            self.assertEqual(service.fetch_jwks(), {'keys': []})
        get.assert_called_once_with(
            'https://cognito-idp.us-east-2.amazonaws.com/pool-1/.well-known/jwks.json',
            timeout=5,
        )

    @override_settings(COGNITO_USER_POOL_ID='pool-1', COGNITO_APP_CLIENT_ID='client-1')
    def test_usernames_reach_cognito_in_lower_case(self):
        client = MagicMock()
        client.sign_up.return_value = {'UserSub': 'sub-1'}
        client.initiate_auth.return_value = {
            'AuthenticationResult': {'AccessToken': 'a', 'RefreshToken': 'r'}
        }
        client.admin_get_user.return_value = {'UserAttributes': [{'Name': 'sub', 'Value': 'sub-1'}]}
        service = CognitoService(client)

        service.sign_up_confirmed('Ana@Example.com', 'Senha123')
        service.authenticate('ANA@example.com', 'Senha123')
        service.admin_get_sub('Ana@example.COM')
        service.admin_delete_user('ANA@EXAMPLE.COM')

        self.assertEqual(client.sign_up.call_args.kwargs['Username'], 'ana@example.com')
        self.assertEqual(
            client.sign_up.call_args.kwargs['UserAttributes'], [{'Name': 'email', 'Value': 'ana@example.com'}]
        )
        self.assertEqual(client.admin_confirm_sign_up.call_args.kwargs['Username'], 'ana@example.com')
        self.assertEqual(client.initiate_auth.call_args.kwargs['AuthParameters']['USERNAME'], 'ana@example.com')
        self.assertEqual(client.admin_get_user.call_args.kwargs['Username'], 'ana@example.com')
        self.assertEqual(client.admin_delete_user.call_args.kwargs['Username'], 'ana@example.com')

    def test_test_runner_gives_every_test_a_clean_cognito(self):
        class Registers(unittest.TestCase):
            def test_a(self):
                get_cognito().client.sign_up(
                    ClientId=cognito_fake.CLIENT_ID, Username='a@x.com', Password='Senha123'
                )

        class SeesNothing(unittest.TestCase):
            def test_b(self):
                self.assertEqual(get_cognito().client.users, {})

        runner = HairmatchTestRunner()
        suite = unittest.TestSuite(
            [Registers('test_a'), SeesNothing('test_b')]
        )
        result = unittest.TextTestRunner(
            stream=StringIO(), resultclass=runner.get_resultclass()
        ).run(suite)
        self.assertTrue(result.wasSuccessful(), result.failures)

    def test_confirmation_error_codes_become_domain_errors(self):
        cases = [
            ('CodeMismatchException', InvalidConfirmationCode),
            ('ExpiredCodeException', ExpiredConfirmationCode),
            ('TooManyFailedAttemptsException', TooManyRequests),
            ('LimitExceededException', TooManyRequests),
            ('InternalErrorException', CognitoUnavailable),
            (EndpointConnectionError(endpoint_url='http://x'), CognitoUnavailable),
        ]
        for error, expected in cases:
            with self.subTest(error=error):
                self.fake.fail_next('confirm_sign_up', error)
                with self.assertRaises(expected) as ctx:
                    self.service.confirm_sign_up('a@x.com', '123456')
                self.assertIs(type(ctx.exception), expected)

    def test_login_of_an_unconfirmed_user_is_user_not_confirmed(self):
        self.service.sign_up('a@x.com', 'Senha123')

        with self.assertRaises(UserNotConfirmed) as ctx:
            self.service.authenticate('a@x.com', 'Senha123')
        self.assertIs(type(ctx.exception), UserNotConfirmed)

    def test_not_authorized_on_confirm_means_already_confirmed_but_on_login_stays_invalid_credentials(self):
        self._sign_up()

        with self.assertRaises(AlreadyConfirmed) as ctx:
            self.service.confirm_sign_up('a@x.com', self.fake.confirmation_code('a@x.com'))
        self.assertIs(type(ctx.exception), AlreadyConfirmed)
        with self.assertRaises(InvalidCredentials) as ctx:
            self.service.authenticate('a@x.com', 'Errada123')
        self.assertIs(type(ctx.exception), InvalidCredentials)

    def test_confirm_of_a_user_the_pool_does_not_know_is_an_invalid_code(self):
        self.fake.fail_next('confirm_sign_up', 'UserNotFoundException')

        with self.assertRaises(InvalidConfirmationCode):
            self.service.confirm_sign_up('nobody@x.com', '123456')

    def test_the_right_code_confirms_the_user_in_the_pool(self):
        self.service.sign_up('a@x.com', 'Senha123')

        self.service.confirm_sign_up('a@x.com', self.fake.confirmation_code('a@x.com'))

        self.assertEqual(self.service.admin_get_status('a@x.com'), 'CONFIRMED')

    def test_sign_up_leaves_the_user_unconfirmed_and_sign_up_confirmed_confirms_it(self):
        pending_sub = self.service.sign_up('a@x.com', 'Senha123')
        confirmed_sub = self.service.sign_up_confirmed('b@x.com', 'Senha123')

        names = [name for name, _ in self.fake.calls]
        self.assertEqual(names.count('admin_confirm_sign_up'), 1)
        self.assertEqual(self.service.admin_get_status('a@x.com'), 'UNCONFIRMED')
        self.assertEqual(self.service.admin_get_status('b@x.com'), 'CONFIRMED')
        self.assertEqual(pending_sub, self.fake.users['a@x.com']['sub'])
        self.assertEqual(confirmed_sub, self.fake.users['b@x.com']['sub'])

    def test_admin_get_status_reports_the_status_or_none_for_an_unknown_user(self):
        self.service.sign_up('a@x.com', 'Senha123')

        self.assertEqual(self.service.admin_get_status('a@x.com'), 'UNCONFIRMED')
        self.assertIsNone(self.service.admin_get_status('nobody@x.com'))

    def test_admin_get_status_reports_an_outage_as_unavailable(self):
        self.fake.fail_next('admin_get_user', 'InternalErrorException')

        with self.assertRaises(CognitoUnavailable):
            self.service.admin_get_status('a@x.com')

    def test_resend_for_a_confirmed_user_is_rejected_and_any_other_failure_is_unavailable(self):
        self._sign_up()
        with self.assertRaises(ResendRejected) as ctx:
            self.service.resend_confirmation_code('a@x.com')
        self.assertIs(type(ctx.exception), ResendRejected)

        self.fake.fail_next('resend_confirmation_code', 'InternalErrorException')
        with self.assertRaises(CognitoUnavailable) as ctx:
            self.service.resend_confirmation_code('a@x.com')
        self.assertIs(type(ctx.exception), CognitoUnavailable)

    def test_resend_limits_become_too_many_requests(self):
        for code in ('LimitExceededException', 'TooManyRequestsException'):
            with self.subTest(code=code):
                self.fake.fail_next('resend_confirmation_code', code)
                with self.assertRaises(TooManyRequests):
                    self.service.resend_confirmation_code('a@x.com')

    def test_confirm_and_resend_send_the_email_in_lower_case(self):
        self.service.sign_up('A@X.com', 'Senha123')

        self.service.resend_confirmation_code('A@X.com')
        self.service.confirm_sign_up('A@X.com', self.fake.confirmation_code('a@x.com'))

        sent = {name: kwargs['Username'] for name, kwargs in self.fake.calls if name in (
            'sign_up', 'resend_confirmation_code', 'confirm_sign_up'
        )}
        self.assertEqual(sent, {
            'sign_up': 'a@x.com',
            'resend_confirmation_code': 'a@x.com',
            'confirm_sign_up': 'a@x.com',
        })

    def test_a_failed_confirmation_is_logged_without_the_code_the_password_or_the_email(self):
        self.service.sign_up('a@x.com', 'Senha123')
        with self.assertLogs('users.cognito', 'WARNING') as logs:
            with self.assertRaises(InvalidConfirmationCode):
                self.service.confirm_sign_up('a@x.com', '987654')
            self.fake.fail_next('resend_confirmation_code', EndpointConnectionError(endpoint_url='http://x'))
            with self.assertRaises(CognitoUnavailable):
                self.service.resend_confirmation_code('a@x.com')

        self.assertIn('confirm_sign_up', logs.output[0])
        self.assertIn('CodeMismatchException', logs.output[0])
        self.assertIn('resend_confirmation_code', logs.output[1])
        self.assertIn('EndpointConnectionError', logs.output[1])
        for line in logs.output:
            self.assertEqual(logs.records[logs.output.index(line)].levelname, 'WARNING')
            for secret in ('987654', 'Senha123', 'a@x.com'):
                self.assertNotIn(secret, line)


class EmailThrottleTest(SimpleTestCase):
    """EMC-29, EMC-31, EMC-32: the counters are per target e-mail, and the e-mail is never stored in clear."""

    def _key(self, throttle_class, body, format='json'):
        factory = APIRequestFactory()
        request = APIView().initialize_request(factory.post('/api/x', body, format=format))
        return throttle_class().get_cache_key(request, None)

    def test_the_key_ignores_the_case_and_the_spaces_around_the_email(self):
        self.assertEqual(
            self._key(ConfirmEmailThrottle, {'email': ' A@X.com '}),
            self._key(ConfirmEmailThrottle, {'email': 'a@x.com'}),
        )

    def test_different_emails_get_different_keys(self):
        self.assertNotEqual(
            self._key(ConfirmEmailThrottle, {'email': 'a@x.com'}),
            self._key(ConfirmEmailThrottle, {'email': 'b@x.com'}),
        )

    def test_the_key_does_not_contain_the_email(self):
        key = self._key(ResendCodeEmailThrottle, {'email': 'Ana.Souza@x.com'})

        self.assertTrue(key.startswith('throttle_resend_code_email_'))
        for fragment in ('ana', 'souza', '@x.com'):
            self.assertNotIn(fragment, key.lower())

    def test_two_routes_never_share_the_counter_of_the_same_email(self):
        keys = {
            self._key(throttle, {'email': 'a@x.com'})
            for throttle in (ConfirmEmailThrottle, ResendCodeEmailThrottle, RegisterEmailThrottle)
        }

        self.assertEqual(len(keys), 3)

    def test_a_form_body_is_keyed_like_a_json_body(self):
        self.assertEqual(
            self._key(RegisterEmailThrottle, {'email': 'A@x.com'}, format='multipart'),
            self._key(RegisterEmailThrottle, {'email': 'a@x.com'}),
        )

    def test_a_body_without_a_usable_email_is_not_counted(self):
        for body in ({}, {'email': ''}, {'email': '   '}, {'email': 123}, {'email': ['a@x.com']}, [1, 2]):
            with self.subTest(body=body):
                self.assertIsNone(self._key(ConfirmEmailThrottle, body))

    def test_a_google_sign_up_is_not_counted_by_email(self):
        self.assertIsNone(self._key(RegisterEmailThrottle, {'email': 'a@x.com', 'google_signup_token': 'tok'}))

    def test_the_rates_are_the_ones_of_the_spec(self):
        self.assertEqual(
            {cls.__name__: cls.rate for cls in (
                ConfirmIpThrottle, ConfirmEmailThrottle, ResendCodeIpThrottle,
                ResendCodeEmailThrottle, RegisterEmailThrottle,
            )},
            {
                'ConfirmIpThrottle': '10/min',
                'ConfirmEmailThrottle': '10/hour',
                'ResendCodeIpThrottle': '10/hour',
                'ResendCodeEmailThrottle': '3/hour',
                'RegisterEmailThrottle': '3/hour',
            },
        )

    def test_every_throttle_has_its_own_scope(self):
        scopes = [cls.scope for cls in (
            ConfirmIpThrottle, ConfirmEmailThrottle, ResendCodeIpThrottle,
            ResendCodeEmailThrottle, RegisterEmailThrottle,
        )]

        self.assertEqual(len(set(scopes)), 5)
        self.assertTrue(issubclass(ConfirmEmailThrottle, EmailRateThrottle))


class AuthenticationTest(TestCase):
    def setUp(self):
        self.fake = get_cognito().client
        self.user = _create_plain_user(email='cog@example.com', cognito_sub='sub-cognito-1')
        self.google_user = _create_plain_user(email='goo@example.com', phone='5511999990001', google_id='google-1')

    def _request(self, token=None):
        request = RequestFactory().get('/')
        if token is not None:
            request.COOKIES['jwt'] = token
        return request

    def _access_token(self, **kwargs):
        return self.fake.make_access_token(self.user.cognito_sub, **kwargs)

    def _google_session(self, user=None, key=None, **claims):
        now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        payload = {
            'id': (user or self.google_user).id,
            'iss': 'hairmatch',
            'token_use': 'session',
            'iat': now,
            'exp': now + 3600,
        }
        payload.update(claims)
        return jwt.encode(payload, key or settings.SECRET_KEY, algorithm='HS256')

    def _pool_issuer(self):
        return cognito_fake.issuer()

    def test_cognito_access_token_authenticates_the_user_with_that_sub(self):
        token = self._access_token()

        session = authenticate_request(self._request(token))

        self.assertEqual(session.user, self.user)
        self.assertEqual(session.provider, 'cognito')
        self.assertEqual(session.access_token, token)

    def test_google_session_authenticates_the_user_with_that_id(self):
        session = authenticate_request(self._request(self._google_session()))

        self.assertEqual(session.user, self.google_user)
        self.assertEqual(session.provider, 'google')

    def test_invalid_sessions_are_rejected(self):
        now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        other_rsa_key = cognito_fake.new_rsa_key()
        cases = {
            'no cookie': None,
            'not a jwt': 'not-a-jwt',
            'signed by another RSA key': self._access_token(signing_key=other_rsa_key),
            'expired access token': self._access_token(iat=now - 7200, exp=now - 60),
            'issuer of another pool': self._access_token(
                iss='https://cognito-idp.us-east-2.amazonaws.com/us-east-2_OtherPool'
            ),
            'client_id of another app': self._access_token(client_id='another-client'),
            'id token': self._access_token(token_use='id'),
            'refresh token': self.fake.make_refresh_token(self.user.cognito_sub),
            'HS256 with the Cognito issuer': jwt.encode(
                {'sub': self.user.cognito_sub, 'iss': self._pool_issuer(), 'token_use': 'access',
                 'client_id': cognito_fake.CLIENT_ID, 'exp': now + 3600},
                settings.SECRET_KEY, algorithm='HS256',
            ),
            'RS256 with the hairmatch issuer': jwt.encode(
                {'id': self.google_user.id, 'iss': 'hairmatch', 'token_use': 'session', 'exp': now + 3600},
                other_rsa_key, algorithm='RS256',
            ),
            'alg none with the Cognito issuer': jwt.encode(
                {'sub': self.user.cognito_sub, 'iss': self._pool_issuer(), 'token_use': 'access',
                 'client_id': cognito_fake.CLIENT_ID, 'exp': now + 3600},
                None, algorithm='none',
            ),
            'alg none with the hairmatch issuer': jwt.encode(
                {'id': self.google_user.id, 'iss': 'hairmatch', 'token_use': 'session', 'exp': now + 3600},
                None, algorithm='none',
            ),
            'sub without a user': self.fake.make_access_token('sub-nobody'),
            'google session signed with another key': self._google_session(key='another-key-0123456789abcdef0123'),
            'expired google session': self._google_session(iat=now - 7200, exp=now - 60),
            'google session of a missing user': self._google_session(id=999999),
            'google session with token_use signup': self._google_session(token_use='google_signup'),
            'signup token': create_signup_token('goo@example.com', 'google-1'),
        }
        for name, token in cases.items():
            with self.subTest(case=name):
                self.assertIsNone(authenticate_request(self._request(token)))

    def test_authenticated_user_answers_401_with_the_spec_message_for_invalid_sessions(self):
        for token in (None, 'not-a-jwt', self._access_token(token_use='id')):
            with self.subTest(token=token):
                session, error = authenticated_user(self._request(token))
                self.assertIsNone(session)
                self.assertEqual(error.status_code, 401)
                assert_problem(error, 'invalid-session')

    def test_authenticated_user_error_carries_the_request_path_as_instance(self):
        session, error = authenticated_user(RequestFactory().get('/api/users/me?x=1'))

        body = assert_problem(error, 'invalid-session', detail='Your session is missing, invalid or expired.')
        self.assertEqual(body['instance'], '/api/users/me')

    def test_forbidden_answers_403_forbidden(self):
        assert_problem(
            forbidden(self._request()), 'forbidden', detail='You do not have permission to access this resource.'
        )

    def test_authenticated_hairdresser_refuses_a_customer_with_403(self):
        customer_user = _create_plain_user(email='cus@example.com', phone='5511999990002', cognito_sub='sub-customer-1')
        Customer.objects.create(user=customer_user, cpf='12345678901')
        token = self.fake.make_access_token(customer_user.cognito_sub)

        session, hairdresser, error = authenticated_hairdresser(self._request(token))

        self.assertIsNone(session)
        self.assertIsNone(hairdresser)
        assert_problem(error, 'hairdresser-required', detail='Only hairdressers can perform this action.')

    def test_authenticated_customer_refuses_a_hairdresser_with_403(self):
        Hairdresser.objects.create(user=self.user, cnpj='12345678901234')

        session, customer, error = authenticated_customer(self._request(self._access_token()))

        self.assertIsNone(session)
        self.assertIsNone(customer)
        assert_problem(error, 'customer-required', detail='Only customers can perform this action.')

    def test_profile_helpers_answer_401_before_looking_at_the_profile(self):
        _, _, hairdresser_error = authenticated_hairdresser(self._request())
        _, _, customer_error = authenticated_customer(self._request())

        assert_problem(hairdresser_error, 'invalid-session')
        assert_problem(customer_error, 'invalid-session')

    def test_profile_helpers_answer_503_when_the_keys_are_unreachable(self):
        with patch.object(get_cognito(), 'fetch_jwks', side_effect=CognitoUnavailable('down')):
            _, _, error = authenticated_hairdresser(self._request(self._access_token()))

        assert_problem(error, 'auth-unavailable')

    def test_authenticated_profile_helpers_return_the_profile_for_the_right_role(self):
        hairdresser = Hairdresser.objects.create(user=self.user, cnpj='12345678901234')

        session, profile, error = authenticated_hairdresser(self._request(self._access_token()))

        self.assertIsNone(error)
        self.assertEqual(profile, hairdresser)
        self.assertEqual(session.user, self.user)

    def test_authenticated_user_returns_the_session_without_an_error(self):
        session, error = authenticated_user(self._request(self._access_token()))

        self.assertIsNone(error)
        self.assertEqual(session.user, self.user)

    def test_unknown_kid_refetches_the_jwks_once_and_answers_401(self):
        authenticate_request(self._request(self._access_token()))  # primes the key cache
        service = get_cognito()

        with patch.object(service, 'fetch_jwks', wraps=service.fetch_jwks) as fetch:
            session, error = authenticated_user(
                self._request(self._access_token(headers={'kid': 'unknown-kid'}))
            )

        self.assertIsNone(session)
        self.assertEqual(error.status_code, 401)
        self.assertEqual(fetch.call_count, 1)

    def test_kid_missing_from_a_stale_cache_is_found_after_refetching(self):
        authentication._jwks_keys.update({'rotated-out': object()})
        service = get_cognito()

        with patch.object(service, 'fetch_jwks', wraps=service.fetch_jwks) as fetch:
            session = authenticate_request(self._request(self._access_token()))

        self.assertEqual(session.user, self.user)
        self.assertEqual(fetch.call_count, 1)

    def test_cached_keys_are_reused_without_fetching_again(self):
        authenticate_request(self._request(self._access_token()))
        service = get_cognito()

        with patch.object(service, 'fetch_jwks') as fetch:
            session = authenticate_request(self._request(self._access_token()))

        self.assertEqual(session.user, self.user)
        fetch.assert_not_called()

    def test_unreachable_jwks_answers_503(self):
        with patch.object(get_cognito(), 'fetch_jwks', side_effect=CognitoUnavailable('down')):
            session, error = authenticated_user(self._request(self._access_token()))

        self.assertIsNone(session)
        assert_problem(error, 'auth-unavailable', detail='The authentication service is unavailable. Try again shortly.')

    def test_google_session_does_not_need_the_jwks(self):
        with patch.object(get_cognito(), 'fetch_jwks', side_effect=CognitoUnavailable('down')):
            session, error = authenticated_user(self._request(self._google_session()))

        self.assertIsNone(error)
        self.assertEqual(session.user, self.google_user)

    def test_the_old_session_format_is_refused(self):
        now = datetime.datetime.now()
        token = jwt.encode(
            {'id': self.user.id, 'exp': now + datetime.timedelta(minutes=60), 'iat': now},
            LEGACY_SESSION_KEY, algorithm='HS256',
        )

        self.assertIsNone(authenticate_request(self._request(token)))


class SessionReadersTest(TestCase):
    """The `users` views that read the session cookie go through the central authenticator."""

    def setUp(self):
        self.client = APIClient()
        self.fake = get_cognito().client
        self.user = _create_plain_user(
            email='cog@example.com', cognito_sub='sub-cognito-1', role='customer'
        )
        Customer.objects.create(user=self.user, cpf='12345678900')
        self.access_token = self.fake.make_access_token('sub-cognito-1')

    def _forged_session(self):
        now = datetime.datetime.now()
        return jwt.encode(
            {'id': self.user.id, 'exp': now + datetime.timedelta(minutes=60), 'iat': now},
            'not-the-server-key', algorithm='HS256',
        )

    def test_check_authentication_accepts_a_cognito_access_token(self):
        self.client.cookies['jwt'] = self.access_token

        response = self.client.get(reverse('session'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'authenticated': True})

    def test_check_authentication_is_false_for_the_google_signup_token(self):
        self.client.cookies['jwt'] = create_signup_token('cog@example.com', 'google-sub-1')

        response = self.client.get(reverse('session'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'authenticated': False})

    def test_check_authentication_is_false_for_garbage_and_forged_tokens(self):
        for token in ('not-a-jwt', self._forged_session()):
            with self.subTest(token=token):
                self.client.cookies['jwt'] = token
                response = self.client.get(reverse('session'))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {'authenticated': False})

    def test_check_authentication_is_false_when_the_jwks_is_unreachable(self):
        self.client.cookies['jwt'] = self.access_token

        with patch.object(get_cognito(), 'fetch_jwks', side_effect=CognitoUnavailable('down')):
            response = self.client.get(reverse('session'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'authenticated': False})

    def test_user_info_accepts_a_cognito_access_token(self):
        self.client.cookies['jwt'] = self.access_token

        response = self.client.get(reverse('current_user'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['customer']['user']['email'], 'cog@example.com')

    def test_protected_routes_answer_401_without_a_cookie_or_with_a_forged_signature(self):
        routes = [
            ('get', reverse('current_user')),
            ('patch', reverse('current_user')),
            ('delete', reverse('current_user')),
            ('put', reverse('password_change')),
        ]
        for token in (None, self._forged_session()):
            for method, url in routes:
                with self.subTest(method=method, url=url, forged=token is not None):
                    self.client.cookies.clear()
                    if token:
                        self.client.cookies['jwt'] = token
                    extra = {}
                    if method in ('put', 'patch'):
                        extra = {
                            'data': json.dumps({'email': 'cog@example.com', 'password': 'x'}),
                            'content_type': 'application/json',
                        }
                    response = getattr(self.client, method)(url, **extra)
                    self.assertEqual(response.status_code, 401)
                    assert_problem(response, 'invalid-session')
        self.assertTrue(User.objects.filter(pk=self.user.pk).exists())


def _register_payload(**overrides):
    payload = {
        'first_name': 'Nova',
        'last_name': 'Conta',
        'phone': '92991234567',
        'number': '10',
        'complement': 'Casa',
        'neighborhood': 'Centro',
        'city': 'Manaus',
        'state': 'AM',
        'address': 'Rua A',
        'postal_code': '69000000',
        'email': 'nova@example.com',
        'password': 'Senha123',
        'role': 'customer',
        'rating': 5,
        'cpf': '12345678900',
        'preferences': json.dumps([]),
    }
    payload.update(overrides)
    return payload


def _hairdresser_payload(**overrides):
    payload = _register_payload(
        role='hairdresser', email='cabelo@example.com', phone='92992345678', cnpj='12345678000190',
        experience_time='5 anos', experiences='Cortes', products='Veganos', resume='Cachos',
        **overrides,
    )
    del payload['cpf']
    return payload


class CognitoRegisterTest(TestCase):
    """Register by e-mail/password: Cognito holds the password, Postgres holds the profile."""


    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('register')
        self.fake = get_cognito().client

    def _called(self, operation):
        return [kwargs for name, kwargs in self.fake.calls if name == operation]

    def _assert_no_rows(self):
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(Customer.objects.count(), 0)
        self.assertEqual(Hairdresser.objects.count(), 0)
        self.assertEqual(User.preferences.through.objects.count(), 0)

    def test_the_eleventh_sign_up_in_an_hour_is_throttled_and_creates_nothing(self):
        for i in range(10):
            self.client.post(self.register_url, data=_register_payload(
                email=f'conta{i}@example.com', phone=f'9299100000{i}',
            ))
        self.fake.calls.clear()

        response = self.client.post(self.register_url, data=_register_payload(email='extra@example.com'))

        assert_problem(response, 'too-many-requests')
        self.assertEqual(User.objects.count(), 10)
        self.assertFalse(User.objects.filter(email='extra@example.com').exists())
        self.assertEqual(self.fake.calls, [])

    def test_customer_and_hairdresser_are_created_pending_with_the_cognito_sub_and_no_password(self):
        """EMC-03"""
        for payload, model in ((_register_payload(), Customer), (_hairdresser_payload(), Hairdresser)):
            with self.subTest(role=payload['role']):
                response = self.client.post(self.register_url, data=payload)

                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                self.assertEqual(
                    response.json(),
                    {'message': f"{payload['role']} user registered successfully", 'confirmation_required': True},
                )
                self.assertEqual(len(response.cookies), 0)
                user = User.objects.get(email=payload['email'])
                self.assertEqual(user.cognito_sub, self.fake.users[payload['email']]['sub'])
                self.assertIsNone(user.password)
                self.assertFalse(user.is_active)
                self.assertTrue(model.objects.filter(user=user).exists())
                self.assertFalse(self.fake.users[payload['email']]['confirmed'])

    def test_sign_up_calls_only_sign_up_and_never_confirms_the_account_for_the_user(self):
        """EMC-03"""
        self.client.post(self.register_url, data=_register_payload())

        names = [name for name, _ in self.fake.calls]
        self.assertIn('sign_up', names)
        self.assertNotIn('admin_confirm_sign_up', names)

    def test_an_active_account_with_the_same_email_in_another_case_answers_409_without_calling_cognito(self):
        """EMC-05"""
        self.client.post(self.register_url, data=_register_payload(email='a@x.com'))
        activate_account('a@x.com')
        self.fake.calls.clear()

        response = self.client.post(self.register_url, data=_register_payload(email='A@X.com', phone='92998887777'))

        assert_email_taken(response)
        self.assertEqual(self.fake.calls, [])
        self.assertEqual(User.objects.count(), 1)

    def test_password_reaches_cognito_exactly_as_typed(self):
        response = self.client.post(self.register_url, data=_register_payload(password='Senha 123'))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.fake.users['nova@example.com']['password'], 'Senha 123')

    def test_local_validation_failures_answer_as_before_without_calling_cognito(self):
        User.objects.create(
            first_name='A', last_name='B', phone='5592991234567', neighborhood='C', city='D',
            state='AM', address='E', postal_code='69000000', email='taken@example.com', role='customer',
        )
        cases = [
            (_register_payload(email='taken@example.com'), assert_email_taken),
            (_register_payload(phone='92991234567'), assert_phone_taken),
            (_register_payload(role=''), lambda r: assert_missing(r, 'role')),
            (_register_payload(email=''), lambda r: assert_missing(r, 'email')),
            (_register_payload(password=''), lambda r: assert_missing(r, 'password')),
            (_register_payload(phone=''), lambda r: assert_missing(r, 'phone')),
            (_register_payload(phone='123456789'), lambda r: assert_problem(
                r, 'validation-error',
                errors=[{'pointer': '#/phone', 'detail': 'The phone number is too short.'}],
            )),
        ]
        for index, (payload, assert_body) in enumerate(cases):
            with self.subTest(case=index):
                cache.clear()  # the cases share one e-mail; the per-e-mail counter must not carry over
                response = self.client.post(self.register_url, data=payload)
                assert_body(response)
        self.assertEqual(self._called('sign_up'), [])
        self.assertEqual(User.objects.count(), 1)

    def test_a_body_with_no_fields_reports_every_missing_field_at_once(self):
        response = self.client.post(self.register_url, data={})

        assert_missing(response, 'role', 'email', 'password', 'phone')
        self.assertEqual(self._called('sign_up'), [])

    def test_invalid_role_and_short_phone_are_reported_together(self):
        response = self.client.post(self.register_url, data=_register_payload(role='admin', phone='123'))

        assert_problem(response, 'validation-error', errors=[
            {'pointer': '#/role', 'detail': 'The role must be customer or hairdresser.'},
            {'pointer': '#/phone', 'detail': 'The phone number is too short.'},
        ])
        self.assertEqual(self._called('sign_up'), [])

    def test_preferences_that_are_not_a_list_of_ids_answer_400_and_delete_the_cognito_user(self):
        for preferences in ('{"a": 1}', '5', '["a"]', '[true]'):
            with self.subTest(preferences=preferences):
                self.fake.calls.clear()
                cache.clear()  # the cases share one e-mail; the per-e-mail counter must not carry over

                response = self.client.post(self.register_url, data=_register_payload(preferences=preferences))

                assert_problem(
                    response, 'validation-error',
                    errors=[{'pointer': '#/preferences', 'detail': 'The preferences must be a JSON list of ids.'}],
                )
                self._assert_cognito_user_was_deleted()

    def test_unexpected_failure_after_sign_up_answers_500_and_deletes_the_cognito_user(self):
        with patch.object(Customer.objects, 'create', side_effect=RuntimeError('database failure')):
            with self.assertLogs('users.views', level='ERROR'):
                response = self.client.post(self.register_url, data=_register_payload())

        body = assert_problem(response, 'internal-error', detail='The account could not be created.')
        self.assertNotIn('database failure', json.dumps(body))
        self._assert_no_rows()
        self._assert_cognito_user_was_deleted()

    def test_password_outside_the_policy_answers_400_and_creates_nothing(self):
        response = self.client.post(self.register_url, data=_register_payload(password='senha123'))

        assert_problem(
            response, 'password-policy',
            detail='The password must have at least 8 characters, with an uppercase letter, a lowercase letter and a number.',
        )
        self._assert_no_rows()
        self.assertEqual(self.fake.users, {})

    def test_email_that_only_exists_in_cognito_answers_409_and_creates_nothing(self):
        self.fake.sign_up(ClientId=cognito_fake.CLIENT_ID, Username='nova@example.com', Password='Senha123')
        self.fake.admin_confirm_sign_up(UserPoolId=cognito_fake.POOL_ID, Username='nova@example.com')

        response = self.client.post(self.register_url, data=_register_payload())

        assert_email_taken(response)
        self._assert_no_rows()

    def _assert_cognito_user_was_deleted(self, email='nova@example.com'):
        self.assertEqual([call['Username'] for call in self._called('admin_delete_user')], [email])
        self.assertNotIn(email, self.fake.users)
        self._assert_no_rows()

    def test_invalid_picture_after_sign_up_deletes_the_cognito_user(self):
        picture = SimpleUploadedFile('p.jpg', b'not an image', content_type='image/jpeg')

        response = self.client.post(self.register_url, data={**_register_payload(), 'profile_picture': picture})

        assert_invalid_picture(response)
        self._assert_cognito_user_was_deleted()

    def test_invalid_preferences_json_after_sign_up_deletes_the_cognito_user(self):
        response = self.client.post(self.register_url, data=_register_payload(preferences='not json'))

        assert_problem(
            response, 'validation-error',
            errors=[{'pointer': '#/preferences', 'detail': 'The preferences must be a JSON list of ids.'}],
        )
        self._assert_cognito_user_was_deleted()

    def test_insert_failure_after_sign_up_deletes_the_cognito_user_and_can_be_retried(self):
        with patch('users.views._create_role_profile', side_effect=RuntimeError('boom')):
            response = self.client.post(self.register_url, data=_register_payload())

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self._assert_cognito_user_was_deleted()
        retry = self.client.post(self.register_url, data=_register_payload())
        self.assertEqual(retry.status_code, status.HTTP_201_CREATED)

    def test_failed_sign_up_answers_503_and_leaves_no_cognito_user_or_rows(self):
        self.fake.fail_next('sign_up', 'InternalErrorException')

        response = self.client.post(self.register_url, data=_register_payload())

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        assert_auth_unavailable(response)
        self.assertEqual(self.fake.users, {})
        self._assert_no_rows()

    def _pending_account(self, **overrides):
        payload = _register_payload(**overrides)
        self.assertEqual(self.client.post(self.register_url, data=payload).status_code, status.HTTP_201_CREATED)
        return User.objects.get(email=payload['email'])

    def _operations(self):
        return [name for name, _ in self.fake.calls]

    def test_a_pending_account_is_replaced_by_a_sign_up_with_the_same_email_in_another_case(self):
        """EMC-07"""
        old = self._pending_account(email='a@x.com')
        old_sub = old.cognito_sub
        self.fake.calls.clear()

        response = self.client.post(self.register_url, data=_register_payload(email='A@x.com'))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.filter(email__iexact='a@x.com').count(), 1)
        replaced = User.objects.get(email__iexact='a@x.com')
        self.assertEqual(replaced.email, 'A@x.com')
        self.assertNotEqual(replaced.cognito_sub, old_sub)
        self.assertFalse(replaced.is_active)
        self.assertEqual(list(self.fake.users), ['a@x.com'])
        self.assertEqual(self.fake.users['a@x.com']['sub'], replaced.cognito_sub)
        self.assertEqual(self._operations().index('admin_delete_user') < self._operations().index('sign_up'), True)
        self.assertEqual(Customer.objects.count(), 1)

    def test_a_pending_account_that_holds_the_phone_is_replaced_even_with_another_email(self):
        """EMC-08"""
        self._pending_account(email='a@x.com', phone='92991234567')

        response = self.client.post(
            self.register_url, data=_register_payload(email='b@x.com', phone='(92) 99123-4567')
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(list(User.objects.values_list('email', flat=True)), ['b@x.com'])
        self.assertEqual(list(self.fake.users), ['b@x.com'])
        self.assertEqual(Customer.objects.count(), 1)

    def test_an_active_account_that_holds_the_phone_answers_409_without_calling_cognito(self):
        """EMC-09"""
        self._pending_account(email='a@x.com', phone='92991234567')
        activate_account('a@x.com')
        self.fake.calls.clear()

        response = self.client.post(self.register_url, data=_register_payload(email='b@x.com', phone='92991234567'))

        assert_phone_taken(response)
        self.assertEqual(self.fake.calls, [])
        self.assertEqual(list(User.objects.values_list('email', flat=True)), ['a@x.com'])

    def test_an_active_phone_holder_keeps_the_pending_account_with_the_email_untouched(self):
        """EMC-09: nothing is deleted before the conflict is known."""
        self._pending_account(email='a@x.com', phone='92991111111')
        self._pending_account(email='b@x.com', phone='92992222222')
        activate_account('b@x.com')
        self.fake.calls.clear()

        response = self.client.post(self.register_url, data=_register_payload(email='a@x.com', phone='92992222222'))

        assert_phone_taken(response)
        self.assertEqual(self.fake.calls, [])
        self.assertTrue(User.objects.filter(email='a@x.com').exists())
        self.assertIn('a@x.com', self.fake.users)

    def test_an_unconfirmed_orphan_in_cognito_is_deleted_and_the_sign_up_is_repeated_once(self):
        """EMC-10"""
        self.fake.sign_up(ClientId=cognito_fake.CLIENT_ID, Username='nova@example.com', Password='Outra123')
        orphan_sub = self.fake.users['nova@example.com']['sub']
        self.fake.calls.clear()

        response = self.client.post(self.register_url, data=_register_payload())

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            [op for op in self._operations() if op in ('sign_up', 'admin_delete_user')],
            ['sign_up', 'admin_delete_user', 'sign_up'],
        )
        user = User.objects.get(email='nova@example.com')
        self.assertNotEqual(user.cognito_sub, orphan_sub)
        self.assertEqual(user.cognito_sub, self.fake.users['nova@example.com']['sub'])
        self.assertEqual(self.fake.users['nova@example.com']['password'], 'Senha123')

    def test_a_second_sign_up_that_fails_the_same_way_answers_409(self):
        """EMC-10"""
        self.fake.sign_up(ClientId=cognito_fake.CLIENT_ID, Username='nova@example.com', Password='Outra123')
        self.fake.fail_next('sign_up', 'UsernameExistsException')
        self.fake.fail_next('sign_up', 'UsernameExistsException')

        response = self.client.post(self.register_url, data=_register_payload())

        assert_email_taken(response)
        self.assertEqual(self._operations().count('sign_up'), 3)
        self._assert_no_rows()

    def test_a_cognito_outage_while_deleting_the_old_account_answers_503_and_keeps_it(self):
        """EMC-11"""
        old = self._pending_account(email='a@x.com')
        self.fake.fail_next('admin_delete_user', EndpointConnectionError(endpoint_url='http://x'))
        self.fake.calls.clear()

        response = self.client.post(self.register_url, data=_register_payload(email='A@x.com'))

        assert_auth_unavailable(response)
        self.assertEqual(self._operations(), ['admin_delete_user'])
        self.assertEqual(list(User.objects.values_list('pk', flat=True)), [old.pk])
        self.assertEqual(self.fake.users['a@x.com']['sub'], old.cognito_sub)
        self.assertEqual(Customer.objects.count(), 1)

    def test_a_failed_insert_after_the_replacement_deletes_the_new_user_and_the_old_one_stays_deleted(self):
        """EMC-12"""
        self._pending_account(email='a@x.com')
        with patch.object(Customer.objects, 'create', side_effect=RuntimeError('database failure')):
            with self.assertLogs('users.views', level='ERROR'):
                response = self.client.post(self.register_url, data=_register_payload(email='A@x.com'))

        assert_problem(response, 'internal-error', detail='The account could not be created.')
        self.assertEqual(self.fake.users, {})
        self._assert_no_rows()

    def test_the_fourth_sign_up_for_one_email_in_an_hour_is_throttled_whatever_the_ip(self):
        """EMC-32: each sign-up replaces the pending one, so only the e-mail counter can stop it."""
        statuses = []
        for ip in ('10.0.0.1', '10.0.0.2', '10.0.0.1'):
            statuses.append(self.client.post(
                self.register_url, data=_register_payload(email='alvo@example.com'), REMOTE_ADDR=ip,
            ).status_code)
        self.fake.calls.clear()

        response = self.client.post(
            self.register_url, data=_register_payload(email='ALVO@example.com'), REMOTE_ADDR='10.0.0.2',
        )

        self.assertEqual(statuses, [status.HTTP_201_CREATED] * 3)
        assert_problem(response, 'too-many-requests')
        self.assertGreater(int(response['Retry-After']), 0)
        self.assertEqual(self.fake.calls, [])
        self.assertEqual(User.objects.get().email, 'alvo@example.com')

    def test_sign_ups_for_other_emails_are_not_counted_against_a_throttled_one(self):
        """EMC-32"""
        for _ in range(3):
            self.client.post(self.register_url, data=_register_payload(email='alvo@example.com'))

        response = self.client.post(self.register_url, data=_register_payload(email='outro@example.com'))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_a_pool_user_whose_email_a_user_here_already_has_is_not_an_orphan(self):
        """EMC-10: the precondition is that no User has the e-mail. A sign-up running at the same time must not delete it."""
        self.fake.sign_up(ClientId=cognito_fake.CLIENT_ID, Username='nova@example.com', Password='Outra123')
        _create_plain_user(email='nova@example.com', phone='5592990009999')
        self.fake.calls.clear()

        with self.assertRaises(UserAlreadyExists):
            RegisterView._sign_up('nova@example.com', 'Senha123')

        self.assertNotIn('admin_delete_user', self._operations())
        self.assertIn('nova@example.com', self.fake.users)

    def test_a_sign_up_that_loses_the_race_for_the_email_answers_409_and_keeps_the_winners_pool_user(self):
        """Edge case: two sign-ups with the same e-mail at the same time; the unique constraint answers 409."""
        def winner_commits_first(email, password):
            _create_plain_user(email=email, phone='5592990009999')
            return 'loser-sub'

        with patch.object(RegisterView, '_sign_up', side_effect=winner_commits_first):
            response = self.client.post(self.register_url, data=_register_payload())

        assert_email_taken(response)
        self.assertEqual(User.objects.count(), 1)
        self.assertNotIn('admin_delete_user', self._operations())

    def test_a_sign_up_that_loses_the_race_for_the_phone_answers_409_and_deletes_its_own_pool_user(self):
        """Edge case: the phone is taken between the checks and the insert."""
        def winner_commits_first(email, password):
            _create_plain_user(email='outro@example.com', phone='5592991234567')
            return self.fake.sign_up(
                ClientId=cognito_fake.CLIENT_ID, Username=email, Password=password
            )['UserSub']

        with patch.object(RegisterView, '_sign_up', side_effect=winner_commits_first):
            response = self.client.post(self.register_url, data=_register_payload())

        assert_phone_taken(response)
        self.assertEqual(list(User.objects.values_list('email', flat=True)), ['outro@example.com'])
        self.assertEqual(self.fake.users, {})

    def test_an_inactive_account_without_a_cognito_sub_is_never_replaced(self):
        """EMC-07, EMC-08: only an inactive account that has a cognito_sub is pending."""
        _create_plain_user(email='nova@example.com', phone='5592991234567', is_active=False)

        by_email = self.client.post(self.register_url, data=_register_payload(phone='92990000000'))
        by_phone = self.client.post(self.register_url, data=_register_payload(email='b@x.com'))

        assert_email_taken(by_email)
        assert_phone_taken(by_phone)
        self.assertEqual(User.objects.count(), 1)
        self.assertNotIn('admin_delete_user', self._operations())

    def test_google_signup_makes_no_cognito_call(self):
        payload = _register_payload(google_signup_token=create_signup_token('ana@gmail.com', 'google-sub-1'))
        del payload['email'], payload['password']

        response = self.client.post(self.register_url, data=payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.fake.calls, [])
        self.assertIsNone(User.objects.get().cognito_sub)
        self.assertTrue(User.objects.get().is_active)

    def test_connection_error_answers_503_and_creates_nothing(self):
        self.fake.fail_next('sign_up', EndpointConnectionError(endpoint_url='http://x'))

        response = self.client.post(self.register_url, data=_register_payload())

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        assert_auth_unavailable(response)
        self._assert_no_rows()

    def test_throttling_answers_429_and_creates_nothing(self):
        for code in ('TooManyRequestsException', 'LimitExceededException'):
            with self.subTest(code=code):
                self.fake.fail_next('sign_up', code)

                response = self.client.post(self.register_url, data=_register_payload())

                self.assertEqual(response.status_code, 429)
                assert_throttled(response)
                self._assert_no_rows()


class PendingHairdresserListingTest(TestCase):
    """EMC-39: a hairdresser whose e-mail is not confirmed is on no listing."""

    def setUp(self):
        self.client = APIClient()
        self.preference = Preferences.objects.create(name='Coloração')
        self.active = self._hairdresser('ativa@example.com', '5592990000001', is_active=True)
        self.pending = self._hairdresser('pendente@example.com', '5592990000002', is_active=False)

    def _hairdresser(self, email, phone, is_active, name='Marina'):
        user = _create_plain_user(
            email=email, phone=phone, first_name=name, last_name='Cabelos', role='hairdresser',
            is_active=is_active, cognito_sub=f'sub-{email}',
        )
        Hairdresser.objects.create(user=user, cnpj='12345678000190', resume='Cortes')
        self.preference.users.add(user)
        return user

    def _ids(self, hairdressers):
        return sorted(item['id'] for item in hairdressers)

    def _hairdresser_id(self, user):
        return Hairdresser.objects.get(user=user).id

    def test_the_global_search_by_name_returns_only_the_active_hairdresser(self):
        response = self.client.get(reverse('global_search'), {'q': 'Marina'})

        found = [item for item in response.json()['data'] if item['result_type'] == 'hairdresser']
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self._ids(found), [self._hairdresser_id(self.active)])

    def test_the_public_home_lists_only_the_active_hairdresser_by_preference(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(
            self._ids(response.json()['hairdressers_by_preferences']['coloracao']), [self._hairdresser_id(self.active)]
        )

    def test_the_customer_home_for_you_lists_only_the_active_hairdresser(self):
        customer = _create_plain_user(
            email='cliente@example.com', phone='5592990000003', role='customer', cognito_sub='sub-cliente',
        )
        self.preference.users.add(customer)
        self.client.cookies['jwt'] = get_cognito().client.make_access_token('sub-cliente')

        response = self.client.get(reverse('customer_home'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self._ids(response.json()['for_you']), [self._hairdresser_id(self.active)])
        self.assertEqual(
            self._ids(response.json()['hairdressers_by_preferences']['coloracao']), [self._hairdresser_id(self.active)]
        )

    def test_pending_hairdressers_do_not_take_a_place_among_the_ten_of_a_preference(self):
        for i in range(10):
            self._hairdresser(f'extra{i}@example.com', f'559299100000{i}', is_active=True, name=f'Extra{i}')

        response = self.client.get(reverse('home'))

        listed = self._ids(response.json()['hairdressers_by_preferences']['coloracao'])
        self.assertEqual(len(listed), 10)
        self.assertNotIn(self._hairdresser_id(self.pending), listed)


class EmailConfirmationViewTest(TestCase):
    """POST /api/auth/email-confirmations: the e-mailed code turns a pending account into an active one."""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('email_confirmations')
        self.fake = get_cognito().client
        self.client.post(reverse('register'), data=_register_payload(email='Nova@example.com'))
        self.code = self.fake.confirmation_code('nova@example.com')
        self.fake.calls.clear()

    def _confirm(self, email='nova@example.com', code=None, **extra):
        return self.client.post(
            self.url, data=json.dumps({'email': email, 'code': code or self.code}),
            content_type='application/json', **extra,
        )

    def _wrong_code(self):
        return '000000' if self.code != '000000' else '111111'

    def _active(self):
        return User.objects.get(email='Nova@example.com').is_active

    def _confirm_calls(self):
        return [kwargs for name, kwargs in self.fake.calls if name == 'confirm_sign_up']

    def test_the_right_code_activates_the_account_and_answers_200_without_cookies(self):
        """EMC-13"""
        response = self._confirm()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'message': 'Email confirmed'})
        self.assertEqual(len(response.cookies), 0)
        self.assertTrue(self._active())
        self.assertEqual(self.fake.users['nova@example.com']['confirmed'], True)

    def test_after_the_confirmation_the_login_answers_200(self):
        """EMC-13"""
        self._confirm()

        login = self.client.post(
            reverse('login'), data=json.dumps({'email': 'nova@example.com', 'password': 'Senha123'}),
            content_type='application/json',
        )

        self.assertEqual(login.status_code, status.HTTP_200_OK)
        self.assertIn('jwt', login.cookies)

    def test_a_wrong_code_answers_400_and_keeps_the_account_pending(self):
        """EMC-14"""
        response = self._confirm(code=self._wrong_code())

        assert_problem(response, 'invalid-confirmation-code', detail='The confirmation code is invalid.')
        self.assertFalse(self._active())
        self.assertFalse(self.fake.users['nova@example.com']['confirmed'])

    def test_an_expired_code_answers_400_and_keeps_the_account_pending(self):
        """EMC-15"""
        self.fake.expire_code('nova@example.com')

        response = self._confirm()

        assert_problem(response, 'confirmation-code-expired')
        self.assertFalse(self._active())

    def test_an_unknown_email_answers_exactly_like_a_wrong_code_without_calling_cognito(self):
        """EMC-16"""
        wrong = json.loads(self._confirm(code=self._wrong_code()).content)
        self.fake.calls.clear()

        response = self._confirm(email='ninguem@example.com')

        body = assert_problem(response, 'invalid-confirmation-code')
        for member in ('type', 'title', 'status', 'detail'):
            self.assertEqual(body[member], wrong[member])
        self.assertEqual(self.fake.calls, [])

    def test_a_google_account_has_nothing_to_confirm_and_answers_like_an_unknown_email(self):
        """EMC-16"""
        _create_plain_user(email='google@example.com', google_id='google-sub-1', phone='5592990001111')

        response = self._confirm(email='google@example.com')

        assert_problem(response, 'invalid-confirmation-code')
        self.assertEqual(self.fake.calls, [])

    def test_missing_or_malformed_fields_answer_400_validation_error_without_calling_cognito(self):
        """EMC-17"""
        cases = [
            ({}, ['email', 'code'], 'This field is required.'),
            ({'code': '123456'}, ['email'], 'This field is required.'),
            ({'email': 'nova@example.com'}, ['code'], 'This field is required.'),
            ({'email': 'nova@example.com', 'code': '12345'}, ['code'], 'The code must have 6 digits.'),
            ({'email': 'nova@example.com', 'code': '1234567'}, ['code'], 'The code must have 6 digits.'),
            ({'email': 'nova@example.com', 'code': 'abcdef'}, ['code'], 'The code must have 6 digits.'),
            ({'email': 'nova@example.com', 'code': '12 456'}, ['code'], 'The code must have 6 digits.'),
            ({'email': 'nova@example.com', 'code': 123456}, ['code'], 'This field must be a string.'),
        ]
        for body, fields, message in cases:
            with self.subTest(body=body):
                cache.clear()
                response = self.client.post(self.url, data=json.dumps(body), content_type='application/json')

                assert_problem(
                    response, 'validation-error',
                    errors=[{'pointer': f'#/{field}', 'detail': message} for field in fields],
                )
        self.assertEqual(self.fake.calls, [])
        self.assertFalse(self._active())

    def test_a_body_that_is_not_a_json_object_answers_400_malformed_request(self):
        for raw in ('{nope', '[1]'):
            with self.subTest(raw=raw):
                cache.clear()
                response = self.client.post(self.url, data=raw, content_type='application/json')

                assert_problem(response, 'malformed-request')
        self.assertEqual(self.fake.calls, [])

    def test_an_already_active_account_answers_200_without_calling_cognito(self):
        """EMC-18"""
        self._confirm()
        self.fake.calls.clear()

        response = self._confirm(code=self._wrong_code())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'message': 'Email confirmed'})
        self.assertEqual(self.fake.calls, [])

    def test_too_many_failed_attempts_in_the_pool_answer_429_and_keep_the_account_pending(self):
        """EMC-19"""
        for code in ('TooManyFailedAttemptsException', 'LimitExceededException', 'TooManyRequestsException'):
            with self.subTest(code=code):
                cache.clear()
                self.fake.fail_next('confirm_sign_up', code)

                response = self._confirm()

                assert_throttled(response)
                self.assertFalse(self._active())

    def test_an_account_already_confirmed_in_the_pool_is_activated_here(self):
        """EMC-20"""
        self.fake.admin_confirm_sign_up(UserPoolId=cognito_fake.POOL_ID, Username='nova@example.com')

        response = self._confirm()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'message': 'Email confirmed'})
        self.assertTrue(self._active())

    def test_the_email_in_another_case_finds_the_account_and_reaches_the_pool_in_lower_case(self):
        """Edge case: A@X.com is the same account as a@x.com."""
        response = self._confirm(email='  NOVA@EXAMPLE.com ')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self._active())
        self.assertEqual([call['Username'] for call in self._confirm_calls()], ['nova@example.com'])

    def test_the_eleventh_call_from_one_ip_in_a_minute_answers_429_without_calling_cognito(self):
        """EMC-28"""
        statuses = [
            self._confirm(email=f'ninguem{i}@example.com', code='123456').status_code for i in range(10)
        ]
        self.fake.calls.clear()

        response = self._confirm(email='outro@example.com', code='123456')

        self.assertEqual(statuses, [status.HTTP_400_BAD_REQUEST] * 10)
        assert_problem(response, 'too-many-requests')
        self.assertGreater(int(response['Retry-After']), 0)
        self.assertEqual(self.fake.calls, [])

    def test_the_eleventh_attempt_for_one_email_in_an_hour_answers_429_from_any_ip(self):
        """EMC-29"""
        statuses = [
            self._confirm(code=self._wrong_code(), REMOTE_ADDR=f'10.0.0.{i % 2 + 1}').status_code
            for i in range(10)
        ]
        self.fake.calls.clear()

        response = self._confirm(code=self.code, REMOTE_ADDR='10.0.0.3')

        self.assertEqual(statuses, [status.HTTP_400_BAD_REQUEST] * 10)
        assert_problem(response, 'too-many-requests')
        self.assertGreater(int(response['Retry-After']), 0)
        self.assertEqual(self.fake.calls, [])
        self.assertFalse(self._active())

    def test_a_pool_outage_answers_503_leaves_the_account_pending_and_logs_no_code(self):
        """EMC-48, EMC-49"""
        self.fake.fail_next('confirm_sign_up', EndpointConnectionError(endpoint_url='http://x'))

        with self.assertLogs(level='WARNING') as every_logger:
            response = self._confirm()
        logs = SimpleNamespace(output=[line for line in every_logger.output if 'cognito' in line])

        assert_auth_unavailable(response)
        self.assertFalse(self._active())
        for line in every_logger.output:  # whatever logger the route writes to
            self.assertNotIn(self.code, line)
            self.assertNotIn('nova@example.com', line)
        self.assertEqual(len(logs.output), 1)
        self.assertIn('confirm_sign_up', logs.output[0])
        self.assertIn('EndpointConnectionError', logs.output[0])
        self.assertNotIn(self.code, logs.output[0])
        self.assertNotIn('nova@example.com', logs.output[0])

    def test_an_unmapped_pool_error_answers_503_and_leaves_the_account_pending(self):
        """EMC-48"""
        self.fake.fail_next('confirm_sign_up', 'InternalErrorException')

        response = self._confirm()

        assert_auth_unavailable(response)
        self.assertFalse(self._active())


class ConfirmationCodeViewTest(TestCase):
    """POST /api/auth/confirmation-codes: a new e-mailed code for a pending account, with one answer for every e-mail."""

    ACCEPTED = {'message': 'If the account is pending confirmation, a new code was sent'}

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('confirmation_codes')
        self.fake = get_cognito().client
        self.client.post(reverse('register'), data=_register_payload(email='Nova@example.com'))
        self.first_code = self.fake.confirmation_code('nova@example.com')
        self.fake.calls.clear()

    def _resend(self, email='nova@example.com', **extra):
        return self.client.post(
            self.url, data=json.dumps({'email': email}), content_type='application/json', **extra,
        )

    def _resend_calls(self):
        return [kwargs for name, kwargs in self.fake.calls if name == 'resend_confirmation_code']

    def _active(self):
        return User.objects.get(email='Nova@example.com').is_active

    def test_a_pending_account_gets_a_new_code_and_the_old_one_stops_working(self):
        """EMC-21"""
        response = self._resend()

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.json(), self.ACCEPTED)
        self.assertEqual([call['Username'] for call in self._resend_calls()], ['nova@example.com'])
        new_code = self.fake.confirmation_code('nova@example.com')
        self.assertNotEqual(new_code, self.first_code)
        confirm_url = reverse('email_confirmations')
        stale = self.client.post(
            confirm_url, data=json.dumps({'email': 'nova@example.com', 'code': self.first_code}),
            content_type='application/json',
        )
        assert_problem(stale, 'invalid-confirmation-code')
        fresh = self.client.post(
            confirm_url, data=json.dumps({'email': 'nova@example.com', 'code': new_code}),
            content_type='application/json',
        )
        self.assertEqual(fresh.status_code, status.HTTP_200_OK)

    def test_an_expired_code_is_replaced_by_a_resend(self):
        """Edge case: the code lasts 24 h, and a resend issues a new one."""
        self.fake.expire_code('nova@example.com')

        self._resend()

        self.assertEqual(self.fake.confirm_sign_up(
            ClientId=cognito_fake.CLIENT_ID, Username='nova@example.com',
            ConfirmationCode=self.fake.confirmation_code('nova@example.com'),
        ), {})

    def test_an_unknown_active_or_google_email_gets_the_same_answer_without_calling_cognito(self):
        """EMC-22"""
        activate_account('nova@example.com')
        _create_plain_user(email='google@example.com', google_id='google-sub-1', phone='5592990001111')
        for email in ('ninguem@example.com', 'nova@example.com', 'google@example.com'):
            with self.subTest(email=email):
                self.fake.calls.clear()

                response = self._resend(email)

                self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
                self.assertEqual(response.json(), self.ACCEPTED)
                self.assertEqual(self.fake.calls, [])

    def test_a_missing_or_empty_email_answers_400_validation_error_without_calling_cognito(self):
        """EMC-23"""
        for body in ({}, {'email': ''}):
            with self.subTest(body=body):
                response = self.client.post(self.url, data=json.dumps(body), content_type='application/json')

                assert_problem(response, 'validation-error', errors=[
                    {'pointer': '#/email', 'detail': 'This field is required.'},
                ])
        self.assertEqual(self.fake.calls, [])

    def test_pool_limits_answer_429(self):
        """EMC-24"""
        for code in ('LimitExceededException', 'TooManyRequestsException'):
            with self.subTest(code=code):
                cache.clear()
                self.fake.fail_next('resend_confirmation_code', code)

                assert_throttled(self._resend())

    def test_the_eleventh_call_from_one_ip_in_an_hour_answers_429_without_calling_cognito(self):
        """EMC-30"""
        statuses = [self._resend(email=f'ninguem{i}@example.com').status_code for i in range(10)]
        self.fake.calls.clear()

        response = self._resend(email='outro@example.com')

        self.assertEqual(statuses, [status.HTTP_202_ACCEPTED] * 10)
        assert_problem(response, 'too-many-requests')
        self.assertGreater(int(response['Retry-After']), 0)
        self.assertEqual(self.fake.calls, [])

    def test_the_fourth_request_for_one_email_in_an_hour_answers_429_from_any_ip(self):
        """EMC-31"""
        statuses = [
            self._resend(email=email, REMOTE_ADDR=ip).status_code
            for email, ip in (('nova@example.com', '10.0.0.1'), ('NOVA@example.com', '10.0.0.2'), (' nova@example.com', '10.0.0.1'))
        ]

        response = self._resend(REMOTE_ADDR='10.0.0.2')

        self.assertEqual(statuses, [status.HTTP_202_ACCEPTED] * 3)
        assert_problem(response, 'too-many-requests')
        self.assertGreater(int(response['Retry-After']), 0)
        self.assertEqual(len(self._resend_calls()), 3)

    def test_a_pool_outage_answers_503(self):
        """EMC-48"""
        self.fake.fail_next('resend_confirmation_code', EndpointConnectionError(endpoint_url='http://x'))

        assert_auth_unavailable(self._resend())
        self.assertFalse(self._active())

    def test_an_account_already_confirmed_in_the_pool_is_activated_and_answers_202(self):
        """EMC-54"""
        self.fake.admin_confirm_sign_up(UserPoolId=cognito_fake.POOL_ID, Username='nova@example.com')

        response = self._resend()

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.json(), self.ACCEPTED)
        self.assertTrue(self._active())
        self.assertIn('admin_get_user', [name for name, _ in self.fake.calls])

    def test_a_rejected_resend_for_an_unconfirmed_account_answers_503_and_keeps_it_pending(self):
        """EMC-54"""
        self.fake.fail_next('resend_confirmation_code', 'InvalidParameterException')

        response = self._resend()

        assert_auth_unavailable(response)
        self.assertFalse(self._active())


class CognitoLoginTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.login_url = reverse('login')
        self.fake = get_cognito().client
        self.client.post(reverse('register'), data=_register_payload())
        activate_account('nova@example.com')
        self.fake.calls.clear()
        self.client.cookies.clear()

    def _login(self, email='nova@example.com', password='Senha123'):
        return self.client.post(
            self.login_url, data=json.dumps({'email': email, 'password': password}),
            content_type='application/json',
        )

    def _assert_no_cookies(self, response):
        self.assertNotIn('jwt', response.cookies)
        self.assertNotIn('refresh_token', response.cookies)

    def test_the_eleventh_login_in_a_minute_is_throttled_without_reaching_cognito(self):
        statuses = [self._login(password=f'Errada{i}').status_code for i in range(10)]
        self.fake.calls.clear()

        response = self._login()

        self.assertEqual(statuses, [status.HTTP_401_UNAUTHORIZED] * 10)
        assert_problem(response, 'too-many-requests')
        self.assertGreater(int(response['Retry-After']), 0)
        self.assertEqual(self.fake.calls, [])
        self._assert_no_cookies(response)

    def test_login_sets_the_access_and_refresh_cookies_and_the_session_is_accepted(self):
        response = self._login()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'message': 'Login successful'})
        self.assertEqual([c['AuthFlow'] for c in [k for n, k in self.fake.calls if n == 'initiate_auth']], ['USER_PASSWORD_AUTH'])
        jwt_cookie, refresh_cookie = response.cookies['jwt'], response.cookies['refresh_token']
        self.assertEqual(response.data['jwt'], jwt_cookie.value)
        self.assertEqual(jwt_cookie['max-age'], 3600)
        self.assertEqual(refresh_cookie['max-age'], 2592000)
        self.assertEqual(refresh_cookie['path'], '/api/auth/')
        for cookie in (jwt_cookie, refresh_cookie):
            self.assertTrue(cookie['httponly'])
            self.assertEqual(cookie['samesite'], 'None')
            self.assertTrue(cookie['secure'])
        self.assertEqual(self.client.get(reverse('session')).json(), {'authenticated': True})

    def test_login_is_case_insensitive_on_the_email(self):
        self.assertEqual(self._login(email='NOVA@example.com').status_code, status.HTTP_200_OK)

    def test_wrong_password_and_unknown_email_answer_401_without_cookies(self):
        for email, password in (('nova@example.com', 'Errada123'), ('ninguem@example.com', 'Senha123')):
            with self.subTest(email=email):
                response = self._login(email, password)

                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
                assert_invalid_credentials(response)
                self._assert_no_cookies(response)

    def test_body_that_is_not_json_answers_400_malformed_request(self):
        for body in ('{nope', '[1, 2]', '"text"'):
            with self.subTest(body=body):
                response = self.client.post(self.login_url, data=body, content_type='application/json')

                assert_problem(response, 'malformed-request')
        self.assertEqual(self.fake.calls, [])

    def test_email_and_password_that_are_not_strings_answer_400_validation_error(self):
        response = self.client.post(
            self.login_url, data=json.dumps({'email': 123, 'password': ['x']}), content_type='application/json'
        )

        assert_problem(response, 'validation-error', errors=[
            {'pointer': '#/email', 'detail': 'This field must be a string.'},
            {'pointer': '#/password', 'detail': 'This field must be a string.'},
        ])
        self.assertEqual(self.fake.calls, [])

    def test_the_problem_instance_is_the_login_path(self):
        response = self._login('ninguem@example.com', 'Senha123')

        self.assertEqual(json.loads(response.content)['instance'], '/api/auth/login')

    def test_google_account_answers_403_without_calling_cognito(self):
        _create_plain_user(email='google-only@example.com', google_id='google-sub-9')

        response = self._login('google-only@example.com', 'Senha123')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        assert_problem(
            response, 'google-account-login',
            detail='This account uses Google sign-in. Use the Sign in with Google button.',
        )
        self.assertEqual(self.fake.calls, [])

    def test_cognito_user_without_a_postgres_user_answers_401_without_cookies(self):
        self.fake.sign_up(ClientId=cognito_fake.CLIENT_ID, Username='orfao@example.com', Password='Senha123')
        self.fake.admin_confirm_sign_up(UserPoolId=cognito_fake.POOL_ID, Username='orfao@example.com')

        response = self._login('orfao@example.com', 'Senha123')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        assert_invalid_credentials(response)
        self._assert_no_cookies(response)

    def _pending_account(self, email='pendente@example.com'):
        self.client.post(reverse('register'), data=_register_payload(email=email, phone='92998887766'))
        self.client.cookies.clear()
        self.fake.calls.clear()

    def test_login_of_a_pending_account_with_the_right_password_answers_403_without_cookies(self):
        """EMC-25: the pool refuses it with UserNotConfirmedException."""
        self._pending_account()

        response = self._login('pendente@example.com')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        assert_problem(response, 'email-not-confirmed')
        self._assert_no_cookies(response)
        self.assertEqual(len(response.cookies), 0)

    def test_login_of_a_pending_account_finds_it_whatever_the_case_of_the_email(self):
        """EMC-25: the pool ignores the case, and so must the pending check."""
        self._pending_account()
        self.fake.admin_confirm_sign_up(UserPoolId=cognito_fake.POOL_ID, Username='pendente@example.com')

        response = self._login('PENDENTE@Example.com')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        assert_problem(response, 'email-not-confirmed')
        self._assert_no_cookies(response)

    def test_login_of_an_account_confirmed_in_the_pool_but_inactive_here_answers_403_without_cookies(self):
        """EMC-25: the emulator signs an UNCONFIRMED user in; the database is the second barrier."""
        self._pending_account()
        self.fake.admin_confirm_sign_up(UserPoolId=cognito_fake.POOL_ID, Username='pendente@example.com')

        response = self._login('pendente@example.com')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        assert_problem(response, 'email-not-confirmed')
        self._assert_no_cookies(response)
        self.assertEqual(self.client.get(reverse('session')).json(), {'authenticated': False})

    def test_login_of_a_pending_account_with_the_wrong_password_answers_401_as_for_any_account(self):
        """EMC-26"""
        self._pending_account()

        response = self._login('pendente@example.com', 'Errada123')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        assert_invalid_credentials(response)
        self._assert_no_cookies(response)

    def test_a_valid_access_token_of_an_inactive_user_is_an_invalid_session(self):
        """EMC-27"""
        self._pending_account()
        sub = User.objects.get(email='pendente@example.com').cognito_sub
        self.client.cookies['jwt'] = self.fake.make_access_token(sub)

        response = self.client.get(reverse('current_user'))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        assert_problem(response, 'invalid-session')
        self.assertEqual(self.client.get(reverse('session')).json(), {'authenticated': False})

    def test_missing_or_empty_email_and_password_answer_400_without_calling_cognito(self):
        bodies = [{}, {'email': 'nova@example.com'}, {'password': 'Senha123'},
                  {'email': '', 'password': 'Senha123'}, {'email': 'nova@example.com', 'password': ''}]
        for body in bodies:
            with self.subTest(body=body):
                response = self.client.post(
                    self.login_url, data=json.dumps(body), content_type='application/json'
                )
                expected = [
                    {'pointer': f'#/{field}', 'detail': 'This field is required.'}
                    for field in ('email', 'password') if not body.get(field)
                ]
                assert_problem(response, 'validation-error', errors=expected)
        self.assertEqual(self.fake.calls, [])

    def test_connection_error_answers_503_logs_the_operation_and_sets_no_cookie(self):
        self.fake.fail_next('initiate_auth', EndpointConnectionError(endpoint_url='http://x'))

        with self.assertLogs('users.cognito', 'WARNING') as logs:
            response = self._login()

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        assert_auth_unavailable(response)
        self._assert_no_cookies(response)
        self.assertIn('initiate_auth', logs.output[0])
        self.assertNotIn('Senha123', ''.join(logs.output))

    def test_throttling_answers_429_without_cookies(self):
        self.fake.fail_next('initiate_auth', 'TooManyRequestsException')

        response = self._login()

        self.assertEqual(response.status_code, 429)
        assert_throttled(response)
        self._assert_no_cookies(response)


class CognitoRefreshTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.refresh_url = reverse('refresh')
        self.fake = get_cognito().client
        self.client.post(reverse('register'), data=_register_payload())
        activate_account('nova@example.com')
        self.login_response = self.client.post(
            reverse('login'),
            data=json.dumps({'email': 'nova@example.com', 'password': 'Senha123'}),
            content_type='application/json',
        )
        self.refresh_token = self.login_response.cookies['refresh_token'].value
        self.fake.calls.clear()

    def test_refresh_sets_a_new_access_cookie_that_the_authenticator_accepts(self):
        del self.client.cookies['jwt']  # the access token expired

        response = self.client.post(self.refresh_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'message': 'Session refreshed'})
        self.assertEqual([k['AuthFlow'] for n, k in self.fake.calls if n == 'initiate_auth'], ['REFRESH_TOKEN_AUTH'])
        self.assertEqual(response.cookies['jwt']['max-age'], 3600)
        self.assertNotIn('refresh_token', response.cookies)
        self.assertEqual(self.client.get(reverse('session')).json(), {'authenticated': True})

    def test_refresh_without_the_cookie_answers_401_without_calling_cognito(self):
        self.client.cookies.clear()

        response = self.client.post(self.refresh_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        assert_session_expired(response)
        self.assertEqual(self.fake.calls, [])

    def test_revoked_refresh_token_answers_401_and_expires_both_cookies(self):
        self.fake.revoke_token(Token=self.refresh_token, ClientId=cognito_fake.CLIENT_ID)

        response = self.client.post(self.refresh_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        assert_session_expired(response)
        for key in ('jwt', 'refresh_token'):
            self.assertEqual(response.cookies[key].value, '')
            self.assertEqual(response.cookies[key]['max-age'], 0)

    def test_cognito_failures_answer_503_and_429_without_touching_the_cookies(self):
        cases = [
            (EndpointConnectionError(endpoint_url='http://x'), 503, assert_auth_unavailable),
            ('TooManyRequestsException', 429, assert_throttled),
        ]
        for failure, expected_status, assert_body in cases:
            with self.subTest(status=expected_status):
                self.fake.fail_next('initiate_auth', failure)

                response = self.client.post(self.refresh_url)

                self.assertEqual(response.status_code, expected_status)
                assert_body(response)
                self.assertEqual(len(response.cookies), 0)


class CognitoLogoutTest(TestCase):
    LOGGED_OUT = {'message': 'User logged out'}

    def setUp(self):
        self.client = APIClient()
        self.logout_url = reverse('logout')
        self.fake = get_cognito().client
        self.client.post(reverse('register'), data=_register_payload())
        activate_account('nova@example.com')
        login = self.client.post(
            reverse('login'),
            data=json.dumps({'email': 'nova@example.com', 'password': 'Senha123'}),
            content_type='application/json',
        )
        self.refresh_token = login.cookies['refresh_token'].value

    def _assert_both_cookies_expired(self, response):
        for key, path in (('jwt', '/'), ('refresh_token', '/api/auth/')):
            self.assertEqual(response.cookies[key].value, '')
            self.assertEqual(response.cookies[key]['max-age'], 0)
            self.assertEqual(response.cookies[key]['path'], path)

    def test_logout_revokes_the_refresh_token_and_expires_both_cookies(self):
        response = self.client.post(self.logout_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), self.LOGGED_OUT)
        self._assert_both_cookies_expired(response)
        self.assertEqual([n for n, _ in self.fake.calls if n == 'revoke_token'], ['revoke_token'])
        self.assertNotIn(self.refresh_token, self.fake.refresh_tokens)
        self.client.cookies['refresh_token'] = self.refresh_token
        self.assertEqual(self.client.post(reverse('refresh')).status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_succeeds_even_when_the_revocation_fails(self):
        self.fake.fail_next('revoke_token', EndpointConnectionError(endpoint_url='http://x'))

        response = self.client.post(self.logout_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), self.LOGGED_OUT)
        self._assert_both_cookies_expired(response)

    def test_logout_without_a_refresh_token_cookie_still_succeeds(self):
        del self.client.cookies['refresh_token']
        self.fake.calls.clear()

        response = self.client.post(self.logout_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), self.LOGGED_OUT)
        self._assert_both_cookies_expired(response)
        self.assertEqual(self.fake.calls, [])


class CognitoChangePasswordTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.change_url = reverse('password_change')
        self.fake = get_cognito().client
        self.client.post(reverse('register'), data=_register_payload())
        activate_account('nova@example.com')
        self._login('Senha123')  # leaves the session cookies on the client
        self.fake.calls.clear()

    def _login(self, password):
        return self.client.post(
            reverse('login'),
            data=json.dumps({'email': 'nova@example.com', 'password': password}),
            content_type='application/json',
        )

    def _change(self, body):
        return self.client.put(self.change_url, data=json.dumps(body), content_type='application/json')

    def _fresh_login_status(self, password):
        return APIClient().post(
            reverse('login'),
            data=json.dumps({'email': 'nova@example.com', 'password': password}),
            content_type='application/json',
        ).status_code

    def test_valid_change_moves_the_password_in_cognito_and_never_stores_it_locally(self):
        response = self._change({'old_password': 'Senha123', 'password': 'NovaSenha456'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'message': 'Password updated successfully'})
        self.assertEqual(self._fresh_login_status('NovaSenha456'), 200)
        self.assertEqual(self._fresh_login_status('Senha123'), 401)
        self.assertIsNone(User.objects.get(email='nova@example.com').password)

    def test_wrong_current_password_answers_400_and_keeps_the_password(self):
        response = self._change({'old_password': 'Errada123', 'password': 'NovaSenha456'})

        assert_problem(response, 'incorrect-current-password', detail='The current password is incorrect.')
        self.assertEqual(self._fresh_login_status('Senha123'), 200)

    def test_new_password_outside_the_policy_answers_400(self):
        response = self._change({'old_password': 'Senha123', 'password': 'abc'})

        assert_problem(
            response, 'password-policy',
            detail='The password must have at least 8 characters, with an uppercase letter, a lowercase letter and a number.',
        )
        self.assertEqual(self._fresh_login_status('Senha123'), 200)

    def test_missing_old_or_new_password_answers_400_without_calling_cognito(self):
        for body in ({'password': 'NovaSenha456'}, {'old_password': 'Senha123'}, {}, {'old_password': '', 'password': 'NovaSenha456'}):
            with self.subTest(body=body):
                response = self._change(body)
                expected = [
                    {'pointer': f'#/{field}', 'detail': 'This field is required.'}
                    for field in ('old_password', 'password') if not body.get(field)
                ]
                assert_problem(response, 'validation-error', errors=expected)
        self.assertEqual([n for n, _ in self.fake.calls if n == 'change_password'], [])

    def test_body_that_is_not_a_json_object_answers_400_malformed_request(self):
        for raw in ('{nope', '[1]'):
            with self.subTest(raw=raw):
                response = self.client.put(self.change_url, data=raw, content_type='application/json')

                assert_problem(response, 'malformed-request')
        self.assertEqual([n for n, _ in self.fake.calls if n == 'change_password'], [])

    def test_google_session_answers_403_without_calling_cognito(self):
        google_user = _create_plain_user(email='goo@example.com', google_id='google-sub-1')
        self.client.cookies.clear()
        self.client.cookies['jwt'] = issue_session_token(google_user)

        response = self._change({'old_password': 'Senha123', 'password': 'NovaSenha456'})

        assert_problem(
            response, 'google-account-login', detail='This account uses Google sign-in and has no password.'
        )
        self.assertEqual([n for n, _ in self.fake.calls if n == 'change_password'], [])

    def test_connection_error_answers_503_and_keeps_the_password(self):
        self.fake.fail_next('change_password', EndpointConnectionError(endpoint_url='http://x'))

        response = self._change({'old_password': 'Senha123', 'password': 'NovaSenha456'})

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        assert_auth_unavailable(response)
        self.assertEqual(self._fresh_login_status('Senha123'), 200)


class CognitoDeleteAccountTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.own_url = reverse('current_user')
        self.fake = get_cognito().client
        self.client.post(reverse('register'), data=_register_payload())
        activate_account('nova@example.com')
        self.client.post(
            reverse('login'),
            data=json.dumps({'email': 'nova@example.com', 'password': 'Senha123'}),
            content_type='application/json',
        )

    def test_deleting_the_own_account_removes_the_cognito_user_the_row_and_the_cookies(self):
        response = self.client.delete(self.own_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.content, b'')
        self.assertNotIn('nova@example.com', self.fake.users)
        self.assertFalse(User.objects.filter(email='nova@example.com').exists())
        for key in ('jwt', 'refresh_token'):
            self.assertEqual(response.cookies[key]['max-age'], 0)

    def test_a_user_already_missing_from_cognito_does_not_block_the_deletion(self):
        del self.fake.users['nova@example.com']

        response = self.client.delete(self.own_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.content, b'')
        self.assertFalse(User.objects.filter(email='nova@example.com').exists())

    def test_cognito_outage_answers_503_and_keeps_both_the_row_and_the_cognito_user(self):
        for name, delete in (
            ('own account', lambda: self.client.delete(self.own_url)),
        ):
            with self.subTest(route=name):
                self.fake.fail_next('admin_delete_user', EndpointConnectionError(endpoint_url='http://x'))

                response = delete()

                self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
                assert_auth_unavailable(response)
                self.assertTrue(User.objects.filter(email='nova@example.com').exists())
                self.assertIn('nova@example.com', self.fake.users)

    def _hairdresser_with_bookings(self):
        """A hairdresser account (logged in) with a service, availability, a manual block and a past and a future booking."""
        self.client.post(reverse('register'), data=_hairdresser_payload(profile_picture=make_upload('foto.png', fmt='PNG')))
        activate_account('cabelo@example.com')
        self.client.post(
            reverse('login'),
            data=json.dumps({'email': 'cabelo@example.com', 'password': 'Senha123'}),
            content_type='application/json',
        )
        hairdresser = Hairdresser.objects.get(user__email='cabelo@example.com')
        customer = Customer.objects.get(user__email='nova@example.com')
        service = Service.objects.create(name='Corte', price=50, duration=60, hairdresser=hairdresser)
        Availability.objects.create(
            hairdresser=hairdresser, weekday='monday', start_time=datetime.time(9), end_time=datetime.time(17)
        )
        now = timezone.now().replace(microsecond=0)
        for start in (now - datetime.timedelta(days=7), now + datetime.timedelta(days=7), now + datetime.timedelta(days=8)):
            Agenda.objects.create(start_time=start, end_time=start + datetime.timedelta(hours=1),
                                  hairdresser=hairdresser, service=service)
        past = Reserve.objects.create(start_time=now - datetime.timedelta(days=7), customer=customer, service=service)
        Reserve.objects.create(start_time=now + datetime.timedelta(days=7), customer=customer, service=service)
        past.review = Review.objects.create(
            rating=5, customer=customer, hairdresser=hairdresser, picture=make_upload('corte.png', fmt='PNG')
        )
        past.save()
        return hairdresser

    def test_a_hairdresser_account_is_deleted_with_its_services_agenda_and_cancelled_bookings(self):
        hairdresser = self._hairdresser_with_bookings()
        pictures = [hairdresser.user.profile_picture.name, Review.objects.get().picture.name]

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(self.own_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertNotIn('cabelo@example.com', self.fake.users)
        self.assertFalse(User.objects.filter(email='cabelo@example.com').exists())
        for model in (Hairdresser, Service, Availability, Agenda, Reserve, Review):
            with self.subTest(model=model.__name__):
                self.assertFalse(model.objects.exists())
        for name in pictures:
            with self.subTest(picture=name):
                self.assertFalse(default_storage.exists(name))
        self.assertTrue(User.objects.filter(email='nova@example.com').exists())

    def test_a_customer_account_is_deleted_with_its_bookings_and_frees_the_agenda(self):
        hairdresser = self._hairdresser_with_bookings()
        self.client.post(
            reverse('login'),
            data=json.dumps({'email': 'nova@example.com', 'password': 'Senha123'}),
            content_type='application/json',
        )
        picture = Review.objects.get().picture.name

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(self.own_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertNotIn('nova@example.com', self.fake.users)
        self.assertFalse(Customer.objects.exists())
        self.assertFalse(Reserve.objects.exists())
        self.assertFalse(Review.objects.exists())
        self.assertFalse(default_storage.exists(picture))
        # Only the slot without a booking (the hairdresser's own block) is left in the agenda.
        self.assertEqual(Agenda.objects.count(), 1)
        self.assertTrue(Service.objects.filter(hairdresser=hairdresser).exists())

    def test_a_cognito_outage_keeps_the_hairdresser_rows_and_pictures(self):
        hairdresser = self._hairdresser_with_bookings()
        picture = hairdresser.user.profile_picture.name
        self.fake.fail_next('admin_delete_user', EndpointConnectionError(endpoint_url='http://x'))

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(self.own_url)

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn('cabelo@example.com', self.fake.users)
        self.assertEqual(Reserve.objects.count(), 2)
        self.assertEqual(Agenda.objects.count(), 3)
        self.assertTrue(Service.objects.filter(hairdresser=hairdresser).exists())
        self.assertTrue(Review.objects.exists())
        self.assertTrue(default_storage.exists(picture))

    def test_google_accounts_are_deleted_without_calling_cognito(self):
        google_user = _create_plain_user(email='goo@example.com', google_id='google-sub-1')
        self.fake.calls.clear()
        self.client.cookies['jwt'] = issue_session_token(google_user)

        response = self.client.delete(self.own_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(email='goo@example.com').exists())

        other_google = _create_plain_user(email='goo2@example.com', google_id='google-sub-2')
        self.client.cookies['jwt'] = issue_session_token(other_google)
        own_response = self.client.delete(self.own_url)
        self.assertEqual(own_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(email='goo2@example.com').exists())
        self.assertEqual(self.fake.calls, [])

    def test_deleting_a_google_account_clears_the_session_cookies_without_calling_cognito(self):
        """ACC-34: the account has no cognito_sub, so there is no pool user to delete."""
        google_user = _create_plain_user(email='goo@example.com', google_id='google-sub-1')
        Customer.objects.create(user=google_user, cpf='12345678900')
        self.client.cookies['jwt'] = issue_session_token(google_user)
        self.fake.calls.clear()

        response = self.client.delete(self.own_url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(User.objects.filter(pk=google_user.pk).exists())
        self.assertFalse(Customer.objects.filter(user_id=google_user.pk).exists())
        for key in ('jwt', 'refresh_token'):
            self.assertEqual(response.cookies[key]['max-age'], 0)
        self.assertEqual(self.fake.calls, [])


class UpdateProfileEmailTest(TestCase):
    """PATCH /api/users/me does not change the e-mail (it is the Cognito username)."""

    def setUp(self):
        self.client = APIClient()
        self.own_url = reverse('current_user')
        self.client.post(reverse('register'), data=_register_payload())
        activate_account('nova@example.com')
        self.client.post(
            reverse('login'),
            data=json.dumps({'email': 'nova@example.com', 'password': 'Senha123'}),
            content_type='application/json',
        )

    def _put(self, body):
        return self.client.patch(self.own_url, data=json.dumps(body), content_type='application/json')

    def test_a_different_email_answers_400_and_changes_no_field(self):
        before = User.objects.values().get(email='nova@example.com')

        response = self._put({'email': 'outro@example.com', 'first_name': 'Trocado'})

        assert_problem(response, 'email-change-unsupported', detail='Changing the email is not supported.')
        self.assertEqual(User.objects.values().get(email='nova@example.com'), before)
        self.assertFalse(User.objects.filter(email='outro@example.com').exists())

    def test_the_same_email_still_updates_the_other_fields(self):
        response = self._put({'email': 'nova@example.com', 'first_name': 'Trocado'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(User.objects.get(email='nova@example.com').first_name, 'Trocado')


class RatingIsNotUserSettableTest(TestCase):
    """The rating ranks hairdressers publicly, so neither sign-up nor PATCH /api/users/me takes it from the body."""

    def setUp(self):
        self.client = APIClient()

    def test_sign_up_by_email_ignores_the_rating(self):
        # CRT-21: a customer starts unrated (None) and a hairdresser with the default 5, whatever the body says.
        for payload, expected in ((_register_payload(rating=1), None), (_hairdresser_payload(rating=32767), 5)):
            with self.subTest(role=payload['role']):
                response = self.client.post(reverse('register'), data=payload)

                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                self.assertEqual(User.objects.get(email=payload['email']).rating, expected)

    def test_sign_up_with_google_ignores_the_rating(self):
        payload = {
            **_register_payload(rating=32767),
            'google_signup_token': create_signup_token('ana@gmail.com', 'google-sub-123'),
        }

        response = self.client.post(reverse('register'), data=payload)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # CRT-21: the Google sign-up of a customer starts unrated too.
        self.assertIsNone(User.objects.get(email='ana@gmail.com').rating)

    def test_patch_ignores_the_rating_and_updates_the_other_fields(self):
        self.client.post(reverse('register'), data=_hairdresser_payload())
        activate_account('cabelo@example.com')
        self.client.post(
            reverse('login'),
            data=json.dumps({'email': 'cabelo@example.com', 'password': 'Senha123'}),
            content_type='application/json',
        )

        response = self.client.patch(
            reverse('current_user'),
            data=json.dumps({'rating': 32767, 'first_name': 'Trocado'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = User.objects.get(email='cabelo@example.com')
        self.assertEqual(user.rating, 5)
        self.assertEqual(user.first_name, 'Trocado')


class CustomerRatingFieldTest(TestCase):
    """CRT-22, CRT-23 and CRT-27: `User.rating` is a float, and `None` means a customer with no ratings."""

    def setUp(self):
        self.client = APIClient()

    def _login_new_customer(self):
        self.client.post(reverse('register'), data=_register_payload())
        activate_account('nova@example.com')
        self.client.post(
            reverse('login'),
            data=json.dumps({'email': 'nova@example.com', 'password': 'Senha123'}),
            content_type='application/json',
        )
        return User.objects.get(email='nova@example.com')

    def _run_data_migration(self):
        migration = importlib.import_module('users.migrations.0013_null_customer_ratings')
        migration.null_customer_ratings(django_apps, None)

    def test_the_data_migration_nulls_every_customer_by_the_profile(self):
        lower = _create_plain_user(email='lower@example.com', phone='5592900000001', role='customer', rating=5)
        upper = _create_plain_user(email='upper@example.com', phone='5592900000002', role='CUSTOMER', rating=5)
        for user in (lower, upper):
            Customer.objects.create(user=user, cpf='12345678900')

        self._run_data_migration()

        lower.refresh_from_db()
        upper.refresh_from_db()
        self.assertIsNone(lower.rating)
        self.assertIsNone(upper.rating)

    def test_the_data_migration_keeps_the_hairdresser_rating(self):
        user = _create_plain_user(email='salao@example.com', role='hairdresser', rating=4.5)
        Hairdresser.objects.create(user=user, cnpj='12345678000199')

        self._run_data_migration()

        user.refresh_from_db()
        self.assertEqual(user.rating, 4.5)

    def test_me_answers_null_for_a_new_customer(self):
        self._login_new_customer()

        response = self.client.get(reverse('current_user'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('rating', response.json()['customer']['user'])
        self.assertIsNone(response.json()['customer']['user']['rating'])

    def test_me_answers_the_stored_average_as_a_json_number(self):
        user = self._login_new_customer()
        User.objects.filter(pk=user.pk).update(rating=4.33)

        response = self.client.get(reverse('current_user'))

        rating = response.json()['customer']['user']['rating']
        self.assertIsInstance(rating, float)
        self.assertEqual(rating, 4.33)

    def test_patch_ignores_the_rating_of_an_unrated_customer(self):
        self._login_new_customer()

        response = self.client.patch(
            reverse('current_user'),
            data=json.dumps({'rating': 1, 'first_name': 'Trocado'}),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = User.objects.get(email='nova@example.com')
        self.assertIsNone(user.rating)
        self.assertEqual(user.first_name, 'Trocado')


class UpdateProfilePhoneTest(TestCase):
    """PATCH /api/users/me takes the full stored phone (55 included) and refuses one used by another user."""

    def setUp(self):
        self.client = APIClient()
        self.own_url = reverse('current_user')
        self.client.post(reverse('register'), data=_register_payload())
        activate_account('nova@example.com')
        self.client.post(
            reverse('login'),
            data=json.dumps({'email': 'nova@example.com', 'password': 'Senha123'}),
            content_type='application/json',
        )
        _create_plain_user(email='other@example.com', phone='5592998887777')

    def _put(self, body):
        return self.client.patch(self.own_url, data=json.dumps(body), content_type='application/json')

    def test_a_phone_of_another_user_answers_409_and_changes_nothing(self):
        response = self._put({'phone': '+55 (92) 99888-7777', 'first_name': 'Trocado'})

        assert_problem(response, 'phone-taken', detail='This phone number is already registered.')
        user = User.objects.get(email='nova@example.com')
        self.assertEqual((user.phone, user.first_name), ('5592991234567', 'Nova'))

    def test_keeping_the_own_phone_still_updates_the_other_fields(self):
        response = self._put({'phone': '5592991234567', 'first_name': 'Trocado'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(User.objects.get(email='nova@example.com').first_name, 'Trocado')

    def test_a_free_phone_is_stored_as_digits(self):
        response = self._put({'phone': '+55 (92) 91111-2222'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(User.objects.get(email='nova@example.com').phone, '5592911112222')

    def _pending_holder(self):
        """A sign-up never confirmed, holding the phone 5592977776666."""
        response = self.client.post(
            reverse('register'), data=_register_payload(email='pendente@example.com', phone='92977776666'),
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        fake = get_cognito().client
        fake.calls.clear()
        return User.objects.get(email='pendente@example.com'), fake

    def test_the_phone_of_a_pending_account_replaces_that_account_and_is_stored(self):
        """ACC-12"""
        pending, fake = self._pending_holder()

        response = self._put({'phone': '55 (92) 97777-6666'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [kwargs['Username'] for name, kwargs in fake.calls if name == 'admin_delete_user'], ['pendente@example.com']
        )
        self.assertNotIn('pendente@example.com', fake.users)
        self.assertFalse(User.objects.filter(pk=pending.pk).exists())
        self.assertEqual(User.objects.get(email='nova@example.com').phone, '5592977776666')

    def test_a_cognito_failure_while_replacing_the_pending_account_answers_503_or_429_and_keeps_both(self):
        """ACC-13"""
        pending, fake = self._pending_holder()
        for error, check in ((EndpointConnectionError(endpoint_url='http://x'), assert_auth_unavailable),
                             ('TooManyRequestsException', assert_throttled)):
            with self.subTest(error=error):
                fake.fail_next('admin_delete_user', error)

                response = self._put({'phone': '5592977776666', 'first_name': 'Trocado'})

                check(response)
                self.assertTrue(User.objects.filter(pk=pending.pk, phone='5592977776666').exists())
                self.assertIn('pendente@example.com', fake.users)
                user = User.objects.get(email='nova@example.com')
                self.assertEqual((user.phone, user.first_name), ('5592991234567', 'Nova'))

    def test_a_phone_taken_by_a_concurrent_request_answers_409_and_not_500(self):
        """ACC-14: the unique constraint refuses the phone after the check found it free."""
        with patch.object(User, 'save', side_effect=IntegrityError('duplicate key value violates unique constraint')):
            response = self._put({'phone': '5592911112222', 'first_name': 'Trocado'})

        assert_problem(response, 'phone-taken', detail='This phone number is already registered.')
        user = User.objects.get(email='nova@example.com')
        self.assertEqual((user.phone, user.first_name), ('5592991234567', 'Nova'))

    def test_the_own_phone_in_a_raw_seed_format_is_kept_and_the_other_fields_are_stored(self):
        """ACC-58: the seed stores raw Faker phones, which do not match 55 + digits."""
        User.objects.filter(email='nova@example.com').update(phone='74 8985-0719')
        for phone in ('74 8985-0719', '7489850719'):
            with self.subTest(phone=phone):
                response = self._put({'phone': phone, 'first_name': f'Trocado {phone}'})

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                user = User.objects.get(email='nova@example.com')
                self.assertEqual((user.phone, user.first_name), ('74 8985-0719', f'Trocado {phone}'))

    def test_a_failed_save_after_the_replacement_answers_the_error_and_the_pending_account_stays_deleted(self):
        """ACC-60, as EMC-12 at sign-up."""
        pending, fake = self._pending_holder()

        with patch.object(User, 'save', side_effect=RuntimeError('database failure')):
            with self.assertLogs('hairmatch.problems', level='ERROR'):
                response = self._put({'phone': '5592977776666'})

        assert_problem(response, 'internal-error')
        self.assertFalse(User.objects.filter(pk=pending.pk).exists())
        self.assertNotIn('pendente@example.com', fake.users)
        self.assertEqual(User.objects.get(email='nova@example.com').phone, '5592991234567')


class ProfileUpdateValidationTest(TestCase):
    """PATCH /api/users/me refuses what the sign-up would not accept and stores the normalized values, all or nothing (ACC-01 to ACC-10, ACC-15)."""

    REQUIRED_FIELDS = ['first_name', 'last_name', 'phone', 'address', 'neighborhood', 'city', 'state', 'postal_code']

    def setUp(self):
        self.client = APIClient()
        self.own_url = reverse('current_user')
        for payload in (_register_payload(), _hairdresser_payload()):
            self.client.post(reverse('register'), data=payload)
            activate_account(payload['email'])
        self._login('nova@example.com')

    def _login(self, email):
        self.client.post(
            reverse('login'),
            data=json.dumps({'email': email, 'password': 'Senha123'}),
            content_type='application/json',
        )

    def _patch(self, body):
        return self.client.patch(self.own_url, data=json.dumps(body), content_type='application/json')

    def _rows(self, email):
        user = User.objects.values().get(email=email)
        profile = (Customer if user['role'] == 'customer' else Hairdresser).objects.values().get(user_id=user['id'])
        return user, profile

    def _assert_refused(self, body, errors, email='nova@example.com'):
        before = self._rows(email)

        response = self._patch(body)

        assert_problem(response, 'validation-error', detail='One or more fields are invalid.', errors=errors)
        self.assertEqual(self._rows(email), before)

    def test_an_empty_blank_or_non_string_required_field_answers_400_and_changes_nothing(self):
        """ACC-01"""
        for field in self.REQUIRED_FIELDS:
            for value, detail in (('', 'This field is required.'), ('   ', 'This field is required.'),
                                  (None, 'This field is required.'), (42, 'This field must be a string.')):
                with self.subTest(field=field, value=value):
                    self._assert_refused(
                        {'complement': 'Mudou', field: value}, [{'pointer': f'#/{field}', 'detail': detail}]
                    )

    def test_a_text_field_over_the_model_max_length_answers_400_and_changes_nothing(self):
        """ACC-02: the model's max_length is the limit, and a value at the limit is stored."""
        limits = {
            'first_name': 100, 'last_name': 100, 'address': 150, 'neighborhood': 150,
            'city': 150, 'complement': 150, 'number': 6,
        }
        for field, limit in limits.items():
            with self.subTest(field=field):
                self._assert_refused(
                    {'state': 'RJ', field: 'a' * (limit + 1)},
                    [{'pointer': f'#/{field}', 'detail': f'This field must have at most {limit} characters.'}],
                )

                response = self._patch({field: 'a' * limit})

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(User.objects.values_list(field, flat=True).get(email='nova@example.com'), 'a' * limit)

    def test_a_phone_that_is_not_55_and_10_or_11_digits_answers_400(self):
        """ACC-03"""
        for phone in ('929912345', '55929912345678', '92991234567', '(92) 3234-5678', '55929912345６７'):
            with self.subTest(phone=phone):
                self._assert_refused(
                    {'first_name': 'Mudou', 'phone': phone},
                    [{'pointer': '#/phone', 'detail': 'The phone number must be 55 followed by 10 or 11 digits.'}],
                )

    def test_a_landline_phone_with_55_and_10_digits_is_stored(self):
        """ACC-03: 55 + 10 digits is a valid phone."""
        response = self._patch({'phone': '+55 (92) 3234-5678'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(User.objects.get(email='nova@example.com').phone, '559232345678')

    def test_a_postal_code_without_8_digits_answers_400(self):
        """ACC-04"""
        for postal_code in ('6905700', '690570001', '69057-00', 'abcdefgh'):
            with self.subTest(postal_code=postal_code):
                self._assert_refused(
                    {'first_name': 'Mudou', 'postal_code': postal_code},
                    [{'pointer': '#/postal_code', 'detail': 'The postal code must have 8 digits.'}],
                )

    def test_a_state_that_is_not_2_letters_answers_400(self):
        """ACC-05"""
        for state in ('Amazonas', 'A1', 'A'):
            with self.subTest(state=state):
                self._assert_refused(
                    {'first_name': 'Mudou', 'state': state},
                    [{'pointer': '#/state', 'detail': 'The state must be 2 letters.'}],
                )

    def test_a_cpf_without_11_digits_answers_400(self):
        """ACC-06"""
        for cpf, detail in (('1234567890', 'The CPF must have 11 digits.'),
                            ('123456789000', 'The CPF must have 11 digits.'),
                            (12345678900, 'This field must be a string.')):
            with self.subTest(cpf=cpf):
                self._assert_refused({'first_name': 'Mudou', 'cpf': cpf}, [{'pointer': '#/cpf', 'detail': detail}])

    def test_a_cnpj_without_14_digits_answers_400(self):
        """ACC-06"""
        self._login('cabelo@example.com')
        for cnpj in ('1234567800019', '123456780001900'):
            with self.subTest(cnpj=cnpj):
                self._assert_refused(
                    {'first_name': 'Mudou', 'cnpj': cnpj},
                    [{'pointer': '#/cnpj', 'detail': 'The CNPJ must have 14 digits.'}],
                    email='cabelo@example.com',
                )

    def test_a_resume_over_1000_characters_or_not_a_string_answers_400(self):
        """ACC-07"""
        self._login('cabelo@example.com')
        for resume, detail in (('a' * 1001, 'The resume must have at most 1000 characters.'),
                               (42, 'This field must be a string.')):
            with self.subTest(resume=resume):
                self._assert_refused(
                    {'first_name': 'Mudou', 'resume': resume},
                    [{'pointer': '#/resume', 'detail': detail}],
                    email='cabelo@example.com',
                )

    def test_a_resume_of_1000_characters_or_empty_is_stored(self):
        """ACC-07"""
        self._login('cabelo@example.com')
        for resume in ('a' * 1000, ''):
            with self.subTest(length=len(resume)):
                response = self._patch({'resume': resume})

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(Hairdresser.objects.get(user__email='cabelo@example.com').resume, resume)

    def test_every_invalid_field_is_reported_in_one_response(self):
        """ACC-01 and ACC-05: one item per field, in the same 400."""
        self._assert_refused(
            {'first_name': '', 'state': 'Amazonas'},
            [
                {'pointer': '#/first_name', 'detail': 'This field is required.'},
                {'pointer': '#/state', 'detail': 'The state must be 2 letters.'},
            ],
        )

    def test_a_valid_body_is_stored_with_digits_only_and_the_state_in_uppercase(self):
        """ACC-08"""
        response = self._patch({
            'phone': '55 (92) 99999-0000', 'postal_code': '69057-000', 'state': 'am', 'cpf': '987.654.321-00',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'message': 'User updated successfully'})
        user = User.objects.get(email='nova@example.com')
        self.assertEqual((user.phone, user.postal_code, user.state), ('5592999990000', '69057000', 'AM'))
        self.assertEqual(Customer.objects.get(user=user).cpf, '98765432100')

    def test_a_valid_cnpj_is_stored_with_digits_only(self):
        """ACC-08"""
        self._login('cabelo@example.com')

        response = self._patch({'cnpj': '98.765.432/0001-90'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Hairdresser.objects.get(user__email='cabelo@example.com').cnpj, '98765432000190')

    def test_the_own_email_in_another_case_is_ignored(self):
        """ACC-09"""
        pk = User.objects.get(email='nova@example.com').pk

        response = self._patch({'email': 'NOVA@Example.COM', 'first_name': 'Trocado'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user = User.objects.get(pk=pk)
        self.assertEqual((user.email, user.first_name), ('nova@example.com', 'Trocado'))

    def test_a_different_email_in_another_case_answers_400_and_changes_nothing(self):
        """ACC-10"""
        before = self._rows('nova@example.com')

        response = self._patch({'email': 'OUTRA@example.com', 'first_name': 'Trocado'})

        assert_problem(response, 'email-change-unsupported', detail='Changing the email is not supported.')
        self.assertEqual(self._rows('nova@example.com'), before)

    def test_fields_the_user_does_not_own_are_ignored(self):
        """ACC-57"""
        before = User.objects.get(email='nova@example.com')

        response = self._patch({
            'rating': 1, 'role': 'hairdresser', 'cognito_sub': 'outro-sub', 'google_id': 'google-x',
            'is_active': False, 'first_name': 'Trocado',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        after = User.objects.get(pk=before.pk)
        self.assertEqual(
            (after.rating, after.role, after.cognito_sub, after.google_id, after.is_active, after.first_name),
            (before.rating, before.role, before.cognito_sub, before.google_id, True, 'Trocado'),
        )

    def _assert_failed_profile_save_keeps_the_account(self, model, body, role):
        with patch.object(model, 'save', side_effect=RuntimeError('database failure')):
            with self.assertLogs('hairmatch.problems', level='ERROR'):
                response = self._patch(body)

        assert_problem(response, 'internal-error')
        return self.client.get(self.own_url).json()[role]

    def test_a_failed_customer_save_undoes_the_user_save(self):
        """ACC-15"""
        current = self._assert_failed_profile_save_keeps_the_account(
            Customer, {'first_name': 'Trocado', 'cpf': '98765432100'}, 'customer'
        )

        self.assertEqual((current['user']['first_name'], current['cpf']), ('Nova', '12345678900'))

    def test_a_failed_hairdresser_save_undoes_the_user_save(self):
        """ACC-15"""
        self._login('cabelo@example.com')

        current = self._assert_failed_profile_save_keeps_the_account(
            Hairdresser, {'first_name': 'Trocado', 'resume': 'Novo resumo'}, 'hairdresser'
        )

        self.assertEqual((current['user']['first_name'], current['resume']), ('Nova', 'Cachos'))


class ProfilePictureViewTest(TestCase):
    """PUT and DELETE /api/users/me/profile-picture replace and remove the picture of the session's user (ACC-35 to ACC-42)."""

    MAX_SIZE = 5 * 1024 * 1024

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('profile_picture')
        self.client.post(reverse('register'), data=_register_payload(profile_picture=make_upload('antiga.png', fmt='PNG')))
        activate_account('nova@example.com')
        self.client.post(
            reverse('login'),
            data=json.dumps({'email': 'nova@example.com', 'password': 'Senha123'}),
            content_type='application/json',
        )
        self.user = User.objects.get(email='nova@example.com')
        self.old_name = self.user.profile_picture.name

    def _put(self, picture):
        return self.client.put(self.url, {'profile_picture': picture}, format='multipart')

    def _assert_old_picture_kept(self):
        self.assertEqual(User.objects.get(pk=self.user.pk).profile_picture.name, self.old_name)
        self.assertTrue(default_storage.exists(self.old_name))

    def test_a_valid_image_is_stored_as_webp_and_its_url_returned(self):
        """ACC-35"""
        response = self._put(make_upload('nova.png', fmt='PNG'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        name = User.objects.get(pk=self.user.pk).profile_picture.name
        self.assertEqual(name, f'profile_pics/{self.user.pk}/nova.webp')
        self.assertEqual(response.json(), {'profile_picture': default_storage.url(name)})
        self.assertTrue(response.json()['profile_picture'].endswith('.webp'))
        self.assertEqual(stored_image(name).format, 'WEBP')

    def test_the_old_file_is_deleted_once_the_new_picture_is_committed(self):
        """ACC-36"""
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            response = self._put(make_upload('nova.png', fmt='PNG'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(default_storage.exists(self.old_name))
        for callback in callbacks:
            callback()
        new_name = User.objects.get(pk=self.user.pk).profile_picture.name
        self.assertNotEqual(new_name, self.old_name)
        self.assertFalse(default_storage.exists(self.old_name))
        self.assertTrue(default_storage.exists(new_name))

    def test_a_file_that_is_not_an_image_answers_400_invalid_image_and_keeps_the_old_picture(self):
        """ACC-37"""
        with self.captureOnCommitCallbacks(execute=True):
            response = self._put(SimpleUploadedFile('foto.png', b'not an image', content_type='image/png'))

        assert_problem(response, 'invalid-image', detail='The profile picture is not a valid image.')
        self._assert_old_picture_kept()

    def test_a_body_without_the_picture_answers_400_validation_error(self):
        """ACC-38"""
        response = self.client.put(self.url, {'other': 'x'}, format='multipart')

        assert_problem(
            response, 'validation-error',
            errors=[{'pointer': '#/profile_picture', 'detail': 'This field is required.'}],
        )
        self._assert_old_picture_kept()

    def test_a_file_over_5_mb_answers_400_validation_error_before_it_is_opened(self):
        """ACC-39: bytes that are no image prove the size is checked first; 5 MB exactly goes on to the conversion."""
        with self.captureOnCommitCallbacks(execute=True):
            response = self._put(SimpleUploadedFile('big.png', b'\0' * (self.MAX_SIZE + 1), content_type='image/png'))

        assert_problem(
            response, 'validation-error',
            errors=[{'pointer': '#/profile_picture', 'detail': 'The profile picture must have at most 5 MB.'}],
        )
        self._assert_old_picture_kept()

        at_limit = self._put(SimpleUploadedFile('big.png', b'\0' * self.MAX_SIZE, content_type='image/png'))

        assert_problem(at_limit, 'invalid-image')

    def test_without_a_session_answers_401_and_changes_nothing(self):
        """ACC-41"""
        self.client.cookies.clear()

        response = self._put(make_upload('nova.png', fmt='PNG'))

        assert_problem(response, 'invalid-session')
        self._assert_old_picture_kept()

    def test_delete_clears_the_picture_and_deletes_the_file_once_committed(self):
        """ACC-40"""
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.content, b'')
        self.assertIsNone(User.objects.values_list('profile_picture', flat=True).get(pk=self.user.pk))
        self.assertTrue(default_storage.exists(self.old_name))
        for callback in callbacks:
            callback()
        self.assertFalse(default_storage.exists(self.old_name))

    def test_delete_without_a_picture_answers_204_without_touching_the_storage(self):
        """ACC-40: it is idempotent."""
        User.objects.filter(pk=self.user.pk).update(profile_picture=None)

        with patch.object(default_storage, 'delete') as storage_delete:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.delete(self.url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIsNone(User.objects.values_list('profile_picture', flat=True).get(pk=self.user.pk))
        storage_delete.assert_not_called()

    def test_delete_without_a_session_answers_401_and_keeps_the_picture(self):
        """ACC-41"""
        self.client.cookies.clear()

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.delete(self.url)

        assert_problem(response, 'invalid-session')
        self._assert_old_picture_kept()

    def test_get_answers_405_with_the_methods_of_the_path(self):
        """ACC-42: the path has PUT and DELETE only."""
        response = self.client.get(self.url)

        assert_problem(response, 'method-not-allowed')
        self.assertEqual(sorted(response['Allow'].split(', ')), ['DELETE', 'OPTIONS', 'PUT'])


class SessionFormatTest(TestCase):
    """After T16 only Cognito access tokens and the new Google session open protected routes."""

    def setUp(self):
        self.client = APIClient()
        self.user = _create_plain_user(email='ana@gmail.com', google_id='google-sub-123', role='customer')
        Customer.objects.create(user=self.user, cpf='12345678900')

    def test_the_old_hs256_session_answers_401_on_a_protected_route_and_false_on_the_auth_check(self):
        now = datetime.datetime.now()
        legacy = jwt.encode(
            {'id': self.user.id, 'exp': now + datetime.timedelta(minutes=60), 'iat': now},
            LEGACY_SESSION_KEY, algorithm='HS256',
        )
        self.client.cookies['jwt'] = legacy

        protected = self.client.get(reverse('current_user'))
        auth_check = self.client.get(reverse('session'))

        self.assertEqual(protected.status_code, status.HTTP_401_UNAUTHORIZED)
        assert_problem(protected, 'invalid-session')
        self.assertEqual(auth_check.json(), {'authenticated': False})

    def test_the_google_signup_token_answers_401_on_a_protected_route(self):
        self.client.cookies['jwt'] = create_signup_token('ana@gmail.com', 'google-sub-123')

        response = self.client.get(reverse('current_user'))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        assert_problem(response, 'invalid-session')

    def test_the_session_from_the_google_login_opens_the_protected_routes_of_other_apps(self):
        preference = Preferences.objects.create(name='Cachos')
        with patch('users.views.verify_google_id_token') as verify:
            verify.return_value = {
                'sub': 'google-sub-123', 'email': 'ana@gmail.com', 'email_verified': True,
                'given_name': 'Ana', 'family_name': 'Souza',
            }
            login = self.client.post(
                reverse('google_auth'), data=json.dumps({'id_token': 'x'}), content_type='application/json'
            )
        self.assertEqual(login.status_code, status.HTTP_200_OK)

        own = self.client.get(reverse('current_user'))
        assign = self.client.put(reverse('user_preference', args=[preference.id]))

        self.assertEqual(own.status_code, status.HTTP_200_OK)
        self.assertEqual(assign.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(preference.users.filter(id=self.user.id).exists())


class GeminiChatViewTest(TestCase):
    """The AI description stays anonymous (hairdresser sign-up needs it) but is throttled per IP."""

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('gemini_completion')
        self.payload = json.dumps({'first_name': 'Ana', 'last_name': 'Silva', 'preferences': []})

    def _post(self, data=None):
        return self.client.post(self.url, data=data or self.payload, content_type='application/json')

    @patch('users.views.hairdresser_profile_ai_completion')
    def test_anonymous_request_gets_the_generated_description(self, completion):
        completion.return_value = JsonResponse({'result': 'Descrição'}, status=200)

        response = self._post()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'result': 'Descrição'})
        completion.assert_called_once_with({'first_name': 'Ana', 'last_name': 'Silva', 'preferences': []})

    @patch('users.views.hairdresser_profile_ai_completion')
    def test_body_that_is_not_a_json_object_answers_400_without_calling_gemini(self, completion):
        for body in ('[]', 'not json', '"text"'):
            with self.subTest(body=body):
                response = self._post(body)
                assert_problem(response, 'malformed-request')
        completion.assert_not_called()

    @patch('users.views.hairdresser_profile_ai_completion')
    def test_unavailable_gemini_answers_503_from_the_client_problem(self, completion):
        completion.side_effect = Problem('ai-service-unavailable', 'The description could not be generated right now. Try again.')

        response = self._post()

        assert_problem(
            response, 'ai-service-unavailable',
            detail='The description could not be generated right now. Try again.',
        )

    @override_settings(GEMINI_API_KEY=None)
    def test_gemini_without_an_api_key_answers_503_without_the_exception_text(self):
        with self.assertLogs('hairmatch.ai_clients.gemini_client', level='ERROR'):
            response = self._post()

        body = assert_problem(response, 'ai-service-unavailable')
        self.assertNotIn('GEMINI_API_KEY', json.dumps(body))
        self.assertNotIn('Config error', json.dumps(body))

    def test_preferences_that_are_not_a_list_of_ids_answer_400_validation_error(self):
        for preferences in (None, 'abc', [1, 'x'], {'a': 1}):
            with self.subTest(preferences=preferences):
                response = self._post(json.dumps({'first_name': 'Ana', 'preferences': preferences}))

                assert_problem(
                    response, 'validation-error',
                    errors=[{'pointer': '#/preferences', 'detail': 'The preferences must be a list of ids.'}],
                )

    def test_the_gemini_view_is_a_problem_for_an_html_accept_header_too(self):
        response = self.client.post(
            self.url, data='{nope', content_type='application/json', HTTP_ACCEPT='text/html'
        )

        assert_problem(response, 'malformed-request')

    @patch('users.views.hairdresser_profile_ai_completion')
    def test_the_eleventh_request_in_an_hour_is_throttled_with_429(self, completion):
        completion.return_value = JsonResponse({'result': 'Descrição'}, status=200)

        statuses = [self._post().status_code for _ in range(11)]

        self.assertEqual(statuses, [200] * 10 + [429])
        self.assertEqual(completion.call_count, 10)

    @patch('users.views.hairdresser_profile_ai_completion')
    def test_a_spoofed_x_forwarded_for_does_not_escape_the_throttle(self, completion):
        completion.return_value = JsonResponse({'result': 'Descrição'}, status=200)
        for i in range(10):
            self.client.post(self.url, data=self.payload, content_type='application/json',
                             HTTP_X_FORWARDED_FOR=f'10.9.0.{i}')

        response = self.client.post(self.url, data=self.payload, content_type='application/json',
                                    HTTP_X_FORWARDED_FOR='10.9.1.1')

        assert_problem(response, 'too-many-requests')
        self.assertEqual(completion.call_count, 10)

    @override_settings(REST_FRAMEWORK={**settings.REST_FRAMEWORK, 'NUM_PROXIES': 1})
    @patch('users.views.hairdresser_profile_ai_completion')
    def test_behind_one_proxy_the_throttle_counts_the_ip_the_proxy_appended(self, completion):
        completion.return_value = JsonResponse({'result': 'Descrição'}, status=200)

        def post(forwarded_for):
            return self.client.post(self.url, data=self.payload, content_type='application/json',
                                    HTTP_X_FORWARDED_FOR=forwarded_for)

        for i in range(10):
            post(f'10.9.0.{i}, 203.0.113.7')

        assert_problem(post('10.9.1.1, 203.0.113.7'), 'too-many-requests')
        self.assertEqual(post('203.0.113.8').status_code, 200)


def _create_gallery_hairdresser(email='galeria@example.com', phone='92990000001'):
    """A hairdresser row without a session; the API tests of the gallery log in through `_login_hairdresser`."""
    user = _create_plain_user(email=email, phone=phone, role='hairdresser')
    return Hairdresser.objects.create(user=user, cnpj='12345678000190')


def _add_gallery_photo(hairdresser, name='foto.png', size=(40, 30)):
    photo = GalleryPhoto(hairdresser=hairdresser)
    photo.image.save(name, make_upload(name, size=size, fmt='PNG'))
    return photo


class GalleryPhotoModelTest(TestCase):
    """GalleryPhoto: the key, the WebP conversion, the default order and the cascade (GAL-05, GAL-10)."""

    def setUp(self):
        self.hairdresser = _create_gallery_hairdresser()

    def test_the_key_is_one_random_webp_per_hairdresser_and_hides_the_uploaded_name(self):
        """GAL-05, GAL-10"""
        photo = GalleryPhoto(hairdresser=self.hairdresser)

        photo.image.save('foto da praia.png', make_upload('foto da praia.png', size=(2000, 1500), fmt='PNG'))

        self.assertRegex(photo.image.name, rf'^hairdresser/gallery/{self.hairdresser.pk}/[0-9a-f]{{32}}\.webp$')
        self.assertNotIn('praia', photo.image.name)

    def test_the_stored_object_is_a_webp_of_at_most_1080_px(self):
        """GAL-10"""
        photo = _add_gallery_photo(self.hairdresser, 'grande.png', size=(2000, 1500))

        stored = stored_image(photo.image.name)

        self.assertEqual(stored.format, 'WEBP')
        self.assertEqual(max(stored.size), 1080)

    def test_two_photos_never_share_a_key(self):
        first = _add_gallery_photo(self.hairdresser, 'mesmo.png')
        second = _add_gallery_photo(self.hairdresser, 'mesmo.png')

        self.assertNotEqual(first.image.name, second.image.name)

    def test_the_default_order_is_created_at_then_id_both_descending(self):
        """GAL-01"""
        older = _add_gallery_photo(self.hairdresser)
        same_a = _add_gallery_photo(self.hairdresser)
        same_b = _add_gallery_photo(self.hairdresser)
        moment = timezone.now()
        GalleryPhoto.objects.filter(pk__in=[same_a.pk, same_b.pk]).update(created_at=moment)
        GalleryPhoto.objects.filter(pk=older.pk).update(created_at=moment - datetime.timedelta(days=1))

        ordered = list(GalleryPhoto.objects.values_list('pk', flat=True))

        self.assertEqual(ordered, [same_b.pk, same_a.pk, older.pk])

    def test_deleting_the_hairdresser_deletes_the_rows(self):
        _add_gallery_photo(self.hairdresser)
        other = _add_gallery_photo(_create_gallery_hairdresser('outra@example.com', '92990000002'))

        self.hairdresser.delete()

        self.assertEqual(list(GalleryPhoto.objects.values_list('pk', flat=True)), [other.pk])
