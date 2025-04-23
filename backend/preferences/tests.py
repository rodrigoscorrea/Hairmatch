from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from users.models import User
from preferences.models import Preferences
import jwt
import json
import os
from django.core.files.uploadedfile import SimpleUploadedFile

class PreferencesTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.create_url = reverse('create_preferences')
        self.list_all_url = reverse('list_all_preferences')
        self.list_users = reverse('list_users_per_preference', args=[1])  # Assuming preference ID 1 for testing
        self.login_url = reverse('login')
        self.register_url = reverse('register')
        
        # Create test users
        self.user_payload = {
            "email": "user@example.com",
            "first_name": "Test",
            "last_name": "User",
            "password": "password123",
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
            "rating": 4.5,
        }
        
        # Register user
        self.client.post(
            self.register_url,
            data=json.dumps(self.user_payload),
            content_type='application/json'
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


class CreatePreferencesTest(PreferencesTestCase):
    def test_create_preferences_success(self):
        """Test successful preference creation"""
        preference_data = {
            'name': 'Long Hair'
        }
        
        response = self.client.post(
            self.create_url,
            data=json.dumps(preference_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Preferences.objects.count(), 2)  # 1 from setup + 1 new
        self.assertEqual(Preferences.objects.filter(name='Long Hair').count(), 1)
    
    def test_create_preferences_with_picture(self):
        """Test creating preference with a picture"""
        # This is a simplified test as we can't actually upload files in test
        preference_data = {
            'name': 'Curly Hair',
            'picture': 'test_image_path.jpg'
        }
        
        response = self.client.post(
            self.create_url,
            data=json.dumps(preference_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Preferences.objects.count(), 2)  # 1 from setup + 1 new
        self.assertEqual(Preferences.objects.filter(name='Curly Hair').count(), 1)
    
    def test_create_preferences_no_name(self):
        """Test preference creation with missing name"""
        preference_data = {
            'picture': 'test_image_path.jpg'
        }
        
        response = self.client.post(
            self.create_url,
            data=json.dumps(preference_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        # Preference count should still be 1 from setup
        self.assertEqual(Preferences.objects.count(), 1)


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
            "password": "password456",
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
            "rating": 4.8,
        }
        
        # Register user2
        self.client.post(
            self.register_url,
            data=json.dumps(self.user2_payload),
            content_type='application/json'
        )
        
        # Get user2 object
        self.user2 = User.objects.get(email=self.user2_payload['email'])
        
        # Add users to preferences
        self.preference.users.add(self.user)
        self.preference.users.add(self.user2)
        self.preference2.users.add(self.user2)
        
        # URL for list_users_per_preference
        self.list_users_url1 = reverse('list_users_per_preference', args=[self.preference.id])
        self.list_users_url2 = reverse('list_users_per_preference', args=[self.preference2.id])
        self.list_users_nonexistent_url = reverse('list_users_per_preference', args=[999])  # Non-existent preference ID
    
    def test_list_users_for_valid_preference(self):
        """Test listing users for a valid preference"""
        response = self.client.get(self.list_users_url1)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertEqual(len(response.data['data']), 2)  # Should return 2 users for preference1
        
        # Verify user data in response using fields that are actually returned
        user_first_names = [user['first_name'] for user in response.data['data']]
        user_last_names = [user['last_name'] for user in response.data['data']]
        
        # Check that both users' first and last names are in the response
        self.assertIn(self.user_payload['first_name'], user_first_names)
        self.assertIn(self.user2_payload['first_name'], user_first_names)
        self.assertIn(self.user_payload['last_name'], user_last_names)
        self.assertIn(self.user2_payload['last_name'], user_last_names)
        
        # Alternatively, check for user IDs if they're more reliable
        user_ids = [user['id'] for user in response.data['data']]
        self.assertIn(self.user.id, user_ids)
        self.assertIn(self.user2.id, user_ids)
    
    def test_list_users_for_preference_with_one_user(self):
        """Test listing users for a preference that has only one user"""
        response = self.client.get(self.list_users_url2)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertEqual(len(response.data['data']), 1)  # Should return 1 user for preference2
        
        # Verificar os campos que realmente são retornados pelo UserNameSerializer
        user_data = response.data['data'][0]
        self.assertEqual(user_data['id'], self.user2.id)
        self.assertEqual(user_data['first_name'], self.user2_payload['first_name'])
        self.assertEqual(user_data['last_name'], self.user2_payload['last_name'])
    
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
    
    def test_list_users_with_authenticated_user(self):
        """Test listing users with an authenticated user"""
        # Login as user
        login_response = self.login_user()
        token = login_response.data['jwt']
        
        # Set the JWT token in the client's cookies
        self.client.cookies['jwt'] = token
        
        response = self.client.get(self.list_users_url1)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertEqual(len(response.data['data']), 2)
    

class UpdatePreferencesTest(PreferencesTestCase):
    def test_update_preferences_success(self):
        """Test successful preference update"""
        update_url = reverse('update_preferences', args=[self.preference.id])
        
        update_data = {
            'name': 'Updated Hair Style'
        }
        
        response = self.client.put(
            update_url,
            data=json.dumps(update_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Refresh from database
        self.preference.refresh_from_db()
        self.assertEqual(self.preference.name, 'Updated Hair Style')
    
    def test_update_preferences_not_found(self):
        """Test updating a non-existent preference"""
        update_url = reverse('update_preferences', args=[999])  # Non-existent ID
        
        update_data = {
            'name': 'Updated Hair Style'
        }
        
        response = self.client.put(
            update_url,
            data=json.dumps(update_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class RemovePreferencesTest(PreferencesTestCase):
    def test_remove_preferences_success(self):
        """Test successful preference removal"""
        # Create a preference to be removed
        pref_to_remove = Preferences.objects.create(name="Remove Me")
        remove_url = reverse('remove_preferences', args=[pref_to_remove.id])
        
        response = self.client.delete(remove_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Preferences.objects.count(), 1)  # Only the one from setup remains
        self.assertFalse(Preferences.objects.filter(name="Remove Me").exists())
    
    def test_remove_preferences_not_found(self):
        """Test removing a non-existent preference"""
        remove_url = reverse('remove_preferences', args=[999])  # Non-existent ID
        
        response = self.client.delete(remove_url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Preferences.objects.count(), 1)  # The one from setup remains


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
        self.assertTrue(self.user in self.preference.users.all())
    
    def test_assign_preference_no_auth(self):
        """Test assigning a preference with no authentication"""
        assign_url = reverse('assign_preferences_to_user', args=[self.preference.id])
        
        response = self.client.post(assign_url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
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
        self.assertFalse(self.user in self.preference.users.all())
    
    def test_unassign_preference_no_auth(self):
        """Test unassigning a preference with no authentication"""
        # First assign the preference to the user
        self.preference.users.add(self.user)
        
        unassign_url = reverse('unassign_preferences_from_user', args=[self.preference.id])
        
        response = self.client.post(unassign_url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
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