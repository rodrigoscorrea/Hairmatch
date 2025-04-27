from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from users.models import User, Hairdresser
from availability.models import Availability
from datetime import time, datetime, timedelta
import jwt
import json

class CreateAvailabilityTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.create_url = reverse('create_availability')
        self.login_url = reverse('login')
        self.register_url = reverse('register')
        self.hairdresser_payload = {
            "email": "rodrigosc615@gmail.com",
            "first_name": "Rodrigo Santos",
            "last_name": "o 12",
            "password": "senha123",
            "phone": "+5592984502890",
            "complement": "casa",
            "neighborhood": "centro",
            "city": "manaus",
            "state": "AM",
            "address": "rua francy assis",
            "number": "2229",
            "postal_code": "69050750",
            "rating": 5.0,
            "role": "hairdresser",
            "cnpj": "12345678901212",
            "experience_years": 4,
            "resume": "ele é legal e joga bem"
        }
        
    def test_create_availability_success(self):
        # Register hairdresser
        self.client.post(
            self.register_url,
            data=json.dumps(self.hairdresser_payload),
            content_type='application/json'
        )
        
        # Login
        login_payload = {
            'email': 'rodrigosc615@gmail.com',
            'password': 'senha123'
        }

        response = self.client.post(
            self.login_url,
            data=json.dumps(login_payload),
            content_type='application/json'
        )
        
        # Create availability
        response_creation = self.client.post(
            self.create_url,
            data=json.dumps({
                'weekday': 'monday',
                'start_time': '09:00:00',
                'end_time': '17:00:00'
            }),
            content_type='application/json'
        )

        self.assertEqual(response_creation.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Availability.objects.count(), 1)
        availability = Availability.objects.first()
        self.assertEqual(availability.weekday, 'monday')
        self.assertEqual(str(availability.start_time), '09:00:00')
        self.assertEqual(str(availability.end_time), '17:00:00')
    
    def test_create_availability_success_with_break_time(self):
        # Register hairdresser
        self.client.post(
            self.register_url,
            data=json.dumps(self.hairdresser_payload),
            content_type='application/json'
        )
        
        # Login
        login_payload = {
            'email': 'rodrigosc615@gmail.com',
            'password': 'senha123'
        }

        response = self.client.post(
            self.login_url,
            data=json.dumps(login_payload),
            content_type='application/json'
        )
        
        # Create availability
        response_creation = self.client.post(
            self.create_url,
            data=json.dumps({
                'weekday': 'tuesday',
                'start_time': '09:00:00',
                'end_time': '17:00:00',
                'break_start': '12:00:00',
                'break_end': '13:00:00'
            }),
            content_type='application/json'
        )

        self.assertEqual(response_creation.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Availability.objects.count(), 1)

    def test_create_availability_missing_fields(self):
        # Register hairdresser
        self.client.post(
            self.register_url,
            data=json.dumps(self.hairdresser_payload),
            content_type='application/json'
        )
        
        # Login
        login_payload = {
            'email': 'rodrigosc615@gmail.com',
            'password': 'senha123'
        }

        self.client.post(
            self.login_url,
            data=json.dumps(login_payload),
            content_type='application/json'
        )
        
        # Create availability with missing fields
        response = self.client.post(
            self.create_url,
            data=json.dumps({
                'weekday': 'monday',
                # Missing start_time and end_time
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Availability.objects.count(), 0)
    
    def test_create_availability_no_auth(self):
        # Try to create availability without login
        response = self.client.post(
            self.create_url,
            data=json.dumps({
                'weekday': 'monday',
                'start_time': '09:00:00',
                'end_time': '17:00:00'
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Availability.objects.count(), 0)


class ListAvailabilityTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        
        # Create hairdresser user
        self.hairdresser_payload = {
            "email": "hairdresser@example.com",
            "first_name": "Hair",
            "last_name": "Dresser",
            "password": "password123",
            "phone": "+5592984502890",
            "complement": "casa",
            "neighborhood": "centro",
            "city": "manaus",
            "state": "AM",
            "address": "Salon Street",
            "number": "123",
            "postal_code": "12345678",
            "rating": 5.0,
            "role": "hairdresser",
            "cnpj": "12345678901212",
            "experience_years": 5,
            "resume": "Professional hairdresser"
        }
        
        # Register hairdresser
        self.client.post(
            self.register_url,
            data=json.dumps(self.hairdresser_payload),
            content_type='application/json'
        )
        
        # Get hairdresser
        self.hairdresser = Hairdresser.objects.get(user__email="hairdresser@example.com")
        
        # Create availabilities
        Availability.objects.create(
            hairdresser=self.hairdresser,
            weekday='monday',
            start_time=time(9, 0),
            end_time=time(17, 0)
        )
        
        Availability.objects.create(
            hairdresser=self.hairdresser,
            weekday='tuesday',
            start_time=time(10, 0),
            end_time=time(18, 0)
        )
        
        # Create URL for list availability
        self.list_url = reverse('list_availability', args=[self.hairdresser.id])
        
    def test_list_availability_success(self):
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = json.loads(response.content)
        self.assertEqual(len(data['data']), 2)
        
        # Check first availability
        self.assertEqual(data['data'][0]['weekday'], 'monday')
        self.assertEqual(data['data'][0]['start_time'], '09:00:00')
        self.assertEqual(data['data'][0]['end_time'], '17:00:00')
        
        # Check second availability
        self.assertEqual(data['data'][1]['weekday'], 'tuesday')
        self.assertEqual(data['data'][1]['start_time'], '10:00:00')
        self.assertEqual(data['data'][1]['end_time'], '18:00:00')
        
    def test_list_availability_nonexistent_hairdresser(self):
        # Test with a non-existent hairdresser ID
        nonexistent_url = reverse('list_availability', args=[999])
        response = self.client.get(nonexistent_url)
        
        # The API should return an empty list rather than an error
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = json.loads(response.content)
        self.assertEqual(data['error'], 'Hairdresser not found')


class RemoveAvailabilityTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        
        # Create hairdresser user
        self.hairdresser_payload = {
            "email": "hairdresser@example.com",
            "first_name": "Hair",
            "last_name": "Dresser",
            "password": "password123",
            "phone": "+5592984502890",
            "complement": "casa",
            "neighborhood": "centro",
            "city": "manaus",
            "state": "AM",
            "address": "Salon Street",
            "number": "123",
            "postal_code": "12345678",
            "rating": 5.0,
            "role": "hairdresser",
            "cnpj": "12345678901212",
            "experience_years": 5,
            "resume": "Professional hairdresser"
        }
        
        # Register hairdresser
        self.client.post(
            self.register_url,
            data=json.dumps(self.hairdresser_payload),
            content_type='application/json'
        )
        
        # Get hairdresser
        self.hairdresser = Hairdresser.objects.get(user__email="hairdresser@example.com")
        
        # Create availability
        self.availability = Availability.objects.create(
            hairdresser=self.hairdresser,
            weekday='monday',
            start_time=time(9, 0),
            end_time=time(17, 0)
        )
        
        # Create URL for remove availability
        self.remove_url = reverse('remove_availability', args=[self.availability.id])
        
    def test_remove_availability_success(self):
        response = self.client.delete(self.remove_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Availability.objects.count(), 0)
        
    def test_remove_nonexistent_availability(self):
        # Test with a non-existent availability ID
        nonexistent_url = reverse('remove_availability', args=[999])
        response = self.client.delete(nonexistent_url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(Availability.objects.count(), 1)  # Original availability still exists


class UpdateAvailabilityTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        
        # Create hairdresser user
        self.hairdresser_payload = {
            "email": "hairdresser@example.com",
            "first_name": "Hair",
            "last_name": "Dresser",
            "password": "password123",
            "phone": "+5592984502890",
            "complement": "casa",
            "neighborhood": "centro",
            "city": "manaus",
            "state": "AM",
            "address": "Salon Street",
            "number": "123",
            "postal_code": "12345678",
            "rating": 5.0,
            "role": "hairdresser",
            "cnpj": "12345678901212",
            "experience_years": 5,
            "resume": "Professional hairdresser"
        }
        
        # Register hairdresser
        self.client.post(
            self.register_url,
            data=json.dumps(self.hairdresser_payload),
            content_type='application/json'
        )
        
        # Get hairdresser
        self.hairdresser = Hairdresser.objects.get(user__email="hairdresser@example.com")
        
        # Create availability
        self.availability = Availability.objects.create(
            hairdresser=self.hairdresser,
            weekday='monday',
            start_time=time(9, 0),
            end_time=time(17, 0)
        )
        
        # Create URL for update availability
        self.update_url = reverse('update_availability', args=[self.availability.id])
        
    def test_update_availability_all_fields(self):
        response = self.client.put(
            self.update_url,
            data=json.dumps({
                'weekday': 'wednesday',
                'start_time': '10:00:00',
                'end_time': '18:00:00'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh availability from database
        self.availability.refresh_from_db()
        self.assertEqual(self.availability.weekday, 'wednesday')
        self.assertEqual(str(self.availability.start_time), '10:00:00')
        self.assertEqual(str(self.availability.end_time), '18:00:00')
        
    def test_update_availability_partial(self):
        response = self.client.put(
            self.update_url,
            data=json.dumps({
                'weekday': 'friday'
                # Not updating start_time and end_time
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Refresh availability from database
        self.availability.refresh_from_db()
        self.assertEqual(self.availability.weekday, 'friday')
        self.assertEqual(str(self.availability.start_time), '09:00:00')  # Should remain unchanged
        self.assertEqual(str(self.availability.end_time), '17:00:00')    # Should remain unchanged
        
    def test_update_nonexistent_availability(self):
        # Test with a non-existent availability ID
        nonexistent_url = reverse('update_availability', args=[999])
        response = self.client.put(
            nonexistent_url,
            data=json.dumps({
                'weekday': 'saturday',
                'start_time': '11:00:00',
                'end_time': '19:00:00'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Original availability should remain unchanged
        self.availability.refresh_from_db()
        self.assertEqual(self.availability.weekday, 'monday')
        self.assertEqual(str(self.availability.start_time), '09:00:00')
        self.assertEqual(str(self.availability.end_time), '17:00:00')


class AvailabilityModelTest(TestCase):
    def setUp(self):
        # Create a user with hairdresser role
        self.user = User.objects.create(
            first_name="Test",
            last_name="User",
            email="test@example.com",
            password="testpassword",
            phone="1234567890",
            address="Test Street",
            number="42",
            postal_code="54321",
            role="HAIRDRESSER"
        )
        
        # Create hairdresser
        self.hairdresser = Hairdresser.objects.create(
            user=self.user,
            experience_years=3,
            resume="Test resume",
            cnpj="12345678901234"
        )
        
    def test_availability_model_creation(self):
        availability = Availability.objects.create(
            hairdresser=self.hairdresser,
            weekday='thursday',
            start_time=time(8, 30),
            end_time=time(16, 30)
        )
        
        self.assertEqual(availability.weekday, 'thursday')
        self.assertEqual(str(availability.start_time), '08:30:00')
        self.assertEqual(str(availability.end_time), '16:30:00')
        self.assertEqual(availability.hairdresser, self.hairdresser)
        
    def test_availability_model_relationships(self):
        # Create multiple availabilities for the same hairdresser
        Availability.objects.create(
            hairdresser=self.hairdresser,
            weekday='monday',
            start_time=time(9, 0),
            end_time=time(17, 0)
        )
        
        Availability.objects.create(
            hairdresser=self.hairdresser,
            weekday='wednesday',
            start_time=time(10, 0),
            end_time=time(18, 0)
        )
        
        # Check that hairdresser has the expected number of availabilities
        self.assertEqual(self.hairdresser.availability.count(), 2)
        
        # Check that deleting the hairdresser also deletes the availabilities (cascade)
        hairdresser_id = self.hairdresser.id
        self.user.delete()  # This should also delete the hairdresser due to cascade
        self.assertEqual(Availability.objects.filter(hairdresser_id=hairdresser_id).count(), 0)