from hairmatch.problem_testing import assert_problem
from django.test import TestCase
from django.urls import reverse, NoReverseMatch
from rest_framework.test import APIClient
from rest_framework import status
from users.models import User
from preferences.models import Preferences
import jwt
import json
import os
import datetime
from django.conf import settings
from users.cognito import get_cognito
from users.cognito_fake import new_rsa_key
from django.core.files.uploadedfile import SimpleUploadedFile

class PreferencesTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.list_all_url = reverse('list_all_preferences')
        self.login_url = reverse('login')
        self.register_url = reverse('register')
        
        # Create test users
        self.user_payload = {
            "email": "user@example.com",
            "first_name": "Test",
            "last_name": "User",
            "password": "Password123",
            "phone": "+5592984501111",
            "complement": "Apt 101",
            "neighborhood": "Downtown",
            "city": "Manaus",
            "state": "AM",
            "address": "User Street",
            "number": "123",
            "postal_code": "69050750",
            "role": "customer",
            "cpf": "12345678901",
            "rating": 4,
            "preferences": json.dumps([])
        }
        
        # Register user
        self.client.post(
            self.register_url,
            data=self.user_payload
        )
        
        # Get user object for testing
        self.user = User.objects.get(email=self.user_payload['email'])
        
        # Create test preferences
        self.preference = Preferences.objects.create(
            name="Short Hair"
        )
        
    def login_user(self):
        """Helper method to login as user and get token"""
        login_payload = {
            'email': self.user_payload['email'],
            'password': self.user_payload['password']
        }
        
        response = self.client.post(
            self.login_url,
            data=json.dumps(login_payload),
            content_type='application/json'
        )
        return response


class ListPreferencesTest(PreferencesTestCase):
    def test_list_all_preferences(self):
        """Test listing all preferences"""
        # Create additional preferences for testing
        Preferences.objects.create(name="Wavy Hair")
        Preferences.objects.create(name="Blonde Hair")
        
        response = self.client.get(self.list_all_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)  # 1 from setup + 2 new
    
    def test_list_user_preferences(self):
        """Test listing preferences for a specific user"""
        # Login as user
        login_response = self.login_user()
        
        # Create additional preferences and assign to user
        pref1 = Preferences.objects.create(name="Wavy Hair")
        pref2 = Preferences.objects.create(name="Blonde Hair")
        
        pref1.users.add(self.user)
        self.preference.users.add(self.user)  # Add the one from setup
        
        # Get the list_preferences URL with the user's ID
        list_user_prefs_url = reverse('list_preferences', args=[self.user.id])
        
        # Set the JWT token in the client's cookies
        token = login_response.data['jwt']
        self.client.cookies['jwt'] = token
        
        response = self.client.get(list_user_prefs_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Only the 2 assigned preferences


class ListUsersPerPreferenceTest(PreferencesTestCase):
    def setUp(self):
        super().setUp()
        # Create additional preferences and users for testing
        self.preference2 = Preferences.objects.create(name="Curly Hair")
        
        # Create a second user
        self.user2_payload = {
            "email": "user2@example.com",
            "first_name": "Test2",
            "last_name": "User2",
            "password": "Password456",
            "phone": "+5592984502222",
            "complement": "Apt 202",
            "neighborhood": "Uptown",
            "city": "Manaus",
            "state": "AM",
            "address": "User2 Street",
            "number": "456",
            "postal_code": "69050760",
            "role": "professional",
            "cpf": "98765432109",
            "rating": 4,
            "preferences": json.dumps([])
        }
        
        # Register user2
        self.client.post(
            self.register_url,
            data=self.user2_payload,
        )
        
        # Get user2 object
        self.user2 = User.objects.get(email=self.user2_payload['email'])
        
        # Add users to preferences
        self.preference.users.add(self.user)
        self.preference.users.add(self.user2)
        self.preference2.users.add(self.user2)
        
        # Hairdresser (the only role this listing shows) with both preferences
        self.hairdresser_user = User.objects.create(
            email="hairdresser@example.com", first_name="Hair", last_name="Dresser",
            phone="+5592984503333", neighborhood="Centro", city="Manaus", state="AM",
            address="Salon Street", postal_code="69050750", role="hairdresser",
        )
        self.preference.users.add(self.hairdresser_user)
        self.preference2.users.add(self.hairdresser_user)

        self.login_user()

        # URL for list_users_per_preference
        self.list_users_url1 = reverse('list_users_per_preference', args=[self.preference.id])
        self.list_users_url2 = reverse('list_users_per_preference', args=[self.preference2.id])
        self.list_users_nonexistent_url = reverse('list_users_per_preference', args=[999])  # Non-existent preference ID
    
    def test_list_users_lists_only_hairdressers(self):
        """Customers' names and tastes are not public: only hairdressers are listed"""
        response = self.client.get(self.list_users_url1)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data'], [
            {'id': self.hairdresser_user.id, 'first_name': 'Hair', 'last_name': 'Dresser'}
        ])

    def test_list_users_for_nonexistent_preference(self):
        """Test listing users for a preference that doesn't exist"""
        response = self.client.get(self.list_users_nonexistent_url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        # Convert JsonResponse content to Python dict
        response_content = json.loads(response.content.decode('utf-8'))
        self.assertIn('error', response_content)
        self.assertEqual(response_content['error'], 'Preference not found')
    
    def test_list_users_for_preference_with_no_users(self):
        """Test listing users for a preference that has no users assigned"""
        # Create a new preference with no users
        empty_preference = Preferences.objects.create(name="Empty Preference")
        empty_preference_url = reverse('list_users_per_preference', args=[empty_preference.id])
        
        response = self.client.get(empty_preference_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertEqual(len(response.data['data']), 0)  # Should return empty list

    def test_list_users_without_session_is_refused_with_401(self):
        self.client.cookies.clear()

        response = self.client.get(self.list_users_url1)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn('data', response.json())
    

class AssignPreferenceToUserTest(PreferencesTestCase):
    def test_assign_preference_to_user_success(self):
        """Test successfully assigning a preference to a user"""
        # Login as user
        login_response = self.login_user()
        
        # Set the JWT token in the client's cookies
        token = login_response.data['jwt']
        self.client.cookies['jwt'] = token
        
        assign_url = reverse('assign_preferences_to_user', args=[self.preference.id])
        
        response = self.client.post(assign_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Refresh the preference from the database to get updated users
        self.preference.refresh_from_db()
        self.assertTrue(self.user in self.preference.users.all())
    
    def test_assign_preference_no_auth(self):
        """Test assigning a preference with no authentication"""
        assign_url = reverse('assign_preferences_to_user', args=[self.preference.id])
        
        response = self.client.post(assign_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        assert_problem(response, 'invalid-session')
        self.assertFalse(self.user in self.preference.users.all())
    
    def test_assign_preference_not_found(self):
        """Test assigning a non-existent preference"""
        # Login as user
        login_response = self.login_user()
        
        # Set the JWT token in the client's cookies
        token = login_response.data['jwt']
        self.client.cookies['jwt'] = token
        
        assign_url = reverse('assign_preferences_to_user', args=[999])  # Non-existent ID
        
        response = self.client.post(assign_url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class UnassignPreferenceFromUserTest(PreferencesTestCase):
    def test_unassign_preference_from_user_success(self):
        """Test successfully unassigning a preference from a user"""
        # Login as user
        login_response = self.login_user()
        
        # Set the JWT token in the client's cookies
        token = login_response.data['jwt']
        self.client.cookies['jwt'] = token
        
        # First assign the preference to the user
        self.preference.users.add(self.user)
        
        unassign_url = reverse('unassign_preferences_from_user', args=[self.preference.id])
        
        response = self.client.post(unassign_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Refresh the preference from the database to get updated users
        self.preference.refresh_from_db()
        self.assertFalse(self.user in self.preference.users.all())
    
    def test_unassign_preference_no_auth(self):
        """Test unassigning a preference with no authentication"""
        # First assign the preference to the user
        self.preference.users.add(self.user)
        
        unassign_url = reverse('unassign_preferences_from_user', args=[self.preference.id])
        
        response = self.client.post(unassign_url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        assert_problem(response, 'invalid-session')
        # The user should still be assigned to the preference
        self.assertTrue(self.user in self.preference.users.all())
    
    def test_unassign_preference_not_found(self):
        """Test unassigning a non-existent preference"""
        # Login as user
        login_response = self.login_user()
        
        # Set the JWT token in the client's cookies
        token = login_response.data['jwt']
        self.client.cookies['jwt'] = token
        
        unassign_url = reverse('unassign_preferences_from_user', args=[999])  # Non-existent ID
        
        response = self.client.post(unassign_url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unassign_preference_user_not_assigned(self):
        """Test unassigning a preference that was not assigned to the user"""
        # Login as user (without adding the user to the preference)
        login_response = self.login_user()
        
        # Set the JWT token in the client's cookies
        token = login_response.data['jwt']
        self.client.cookies['jwt'] = token
        
        unassign_url = reverse('unassign_preferences_from_user', args=[self.preference.id])
        
        response = self.client.post(unassign_url)
        
        # Should still return 200 even though nothing changed (idempotent operation)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(self.user in self.preference.users.all())

class PreferenceSessionTest(PreferencesTestCase):
    """The cookie-based assign/unassign routes authenticate through the central authenticator."""

    def setUp(self):
        super().setUp()
        self.user.cognito_sub = 'sub-user'
        self.user.save()
        self.fake = get_cognito().client
        self.assign_url = reverse('assign_preferences_to_user', args=[self.preference.id])
        self.unassign_url = reverse('unassign_preferences_from_user', args=[self.preference.id])

    def _google_token(self):
        now = int(datetime.datetime.now().timestamp())
        return jwt.encode(
            {'id': self.user.id, 'iss': 'hairmatch', 'token_use': 'session',
             'iat': now, 'exp': now + 3600},
            settings.SECRET_KEY, algorithm='HS256',
        )

    def test_routes_accept_a_cognito_access_token_and_a_google_session(self):
        tokens = {
            'cognito': self.fake.make_access_token('sub-user'),
            'google': self._google_token(),
        }
        for kind, token in tokens.items():
            with self.subTest(token=kind):
                self.client.cookies['jwt'] = token

                self.assertEqual(self.client.post(self.assign_url).status_code, 200)
                self.assertTrue(self.preference.users.filter(id=self.user.id).exists())
                self.assertEqual(self.client.post(self.unassign_url).status_code, 200)
                self.assertFalse(self.preference.users.filter(id=self.user.id).exists())

    def test_routes_refuse_a_missing_cookie_and_a_token_signed_with_another_key_with_401(self):
        forged = self.fake.make_access_token('sub-user', signing_key=new_rsa_key())
        self.preference.users.add(self.user)
        for token in (None, forged):
            for url in (self.assign_url, self.unassign_url):
                with self.subTest(url=url, forged=token is not None):
                    self.client.cookies.clear()
                    if token:
                        self.client.cookies['jwt'] = token
                    response = self.client.post(url)
                    self.assertEqual(response.status_code, 401)
                    assert_problem(response, 'invalid-session')
        self.assertTrue(self.preference.users.filter(id=self.user.id).exists())


class RemovedCatalogRoutesTest(PreferencesTestCase):
    """The catalog CRUD and the cookie-less assign had no auth and were removed (#152)."""

    def test_removed_routes_no_longer_exist_and_change_nothing(self):
        routes = [
            ('create_preferences', [], 'post', '/api/preferences/create', {'name': 'PENTEST_INJECTED'}),
            ('update_preferences', [self.preference.id], 'put',
             f'/api/preferences/update/{self.preference.id}', {'name': 'HACKED'}),
            ('remove_preferences', [self.preference.id], 'delete',
             f'/api/preferences/remove/{self.preference.id}', None),
            ('assign_preferences_to_user_no_cookie', [self.preference.id], 'post',
             f'/api/preferences/assign/{self.preference.id}', {'user_id': self.user.id}),
        ]
        for name, args, method, path, body in routes:
            with self.subTest(route=name):
                with self.assertRaises(NoReverseMatch):
                    reverse(name, args=args)
                kwargs = {'data': json.dumps(body), 'content_type': 'application/json'} if body else {}
                response = getattr(self.client, method)(path, **kwargs)
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        self.assertEqual(list(Preferences.objects.values_list('name', flat=True)), ['Short Hair'])
        self.assertFalse(self.preference.users.filter(id=self.user.id).exists())
