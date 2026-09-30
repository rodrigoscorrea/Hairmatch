from hairmatch.problem_testing import assert_problem
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import patch
from users.models import User, Customer, Hairdresser
from availability.models import Availability
from datetime import time, datetime, timedelta
import jwt
import json
from django.conf import settings
from users.cognito import get_cognito
from users.cognito_fake import new_rsa_key

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
            "password": "Senha123",
            "phone": "+5592984502890",
            "complement": "casa",
            "neighborhood": "centro",
            "city": "manaus",
            "state": "AM",
            "address": "rua francy assis",
            "number": "2229",
            "postal_code": "69050750",
            "rating": 5,
            "role": "hairdresser",
            "cnpj": "12345678901212",
            "experience_years": 4,
            "resume": "ele é legal e joga bem",
            "preferences": json.dumps([]),
            'experience_time':'experience_time',
            'experiences':'experiences',
            'products':'products',
            'resume':'resume'
        }
        
    def test_create_availability_success(self):
        # Register hairdresser
        self.client.post(
            self.register_url,
            data=self.hairdresser_payload,
        )
        
        # Login
        login_payload = {
            'email': 'rodrigosc615@gmail.com',
            'password': 'Senha123'
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
            data=self.hairdresser_payload,
        )
        
        # Login
        login_payload = {
            'email': 'rodrigosc615@gmail.com',
            'password': 'Senha123'
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
            data=self.hairdresser_payload,
        )
        
        # Login
        login_payload = {
            'email': 'rodrigosc615@gmail.com',
            'password': 'Senha123'
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

        assert_problem(response, 'validation-error', errors=[
            {'pointer': '#/start_time', 'detail': 'This field is required.'},
            {'pointer': '#/end_time', 'detail': 'This field is required.'},
        ])
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

        assert_problem(response, 'invalid-session')
        self.assertEqual(Availability.objects.count(), 0)


class CreateAvailabilitySessionTest(TestCase):
    """CreateAvailability authenticates through the central authenticator."""

    def setUp(self):
        self.client = APIClient()
        self.fake = get_cognito().client
        self.user = User.objects.create(
            first_name='Ana', last_name='Silva', phone='5592999990000',
            neighborhood='Centro', city='Manaus', state='AM', address='Rua A',
            postal_code='69000000', email='ana@example.com', role='hairdresser',
            cognito_sub='sub-hairdresser-1',
        )
        self.hairdresser = Hairdresser.objects.create(user=self.user, cnpj='12345678901212')
        self.payload = json.dumps({'weekday': 'monday', 'start_time': '09:00:00', 'end_time': '17:00:00'})

    def _post(self):
        return self.client.post(
            reverse('create_availability'), data=self.payload, content_type='application/json'
        )

    def test_cognito_access_token_creates_the_availability_for_that_hairdresser(self):
        self.client.cookies['jwt'] = self.fake.make_access_token('sub-hairdresser-1')

        response = self._post()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Availability.objects.get().hairdresser, self.hairdresser)

    def test_google_session_creates_the_availability_for_that_hairdresser(self):
        now = int(datetime.now().timestamp())
        self.client.cookies['jwt'] = jwt.encode(
            {'id': self.user.id, 'iss': 'hairmatch', 'token_use': 'session', 'iat': now, 'exp': now + 3600},
            settings.SECRET_KEY, algorithm='HS256',
        )

        response = self._post()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Availability.objects.get().hairdresser, self.hairdresser)

    def test_token_signed_with_another_key_is_refused_with_401(self):
        self.client.cookies['jwt'] = self.fake.make_access_token(
            'sub-hairdresser-1', signing_key=new_rsa_key()
        )

        response = self._post()

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        assert_problem(response, 'invalid-session')
        self.assertEqual(Availability.objects.count(), 0)


class CreateMultipleAvailabilityTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        
        # Hairdresser payload similar to the previous test
        self.hairdresser_payload = {
            "email": "rodrigosc615@gmail.com",
            "first_name": "Rodrigo Santos",
            "last_name": "o 12",
            "password": "Senha123",
            "phone": "+5592984502890",
            "complement": "casa",
            "neighborhood": "centro",
            "city": "manaus",
            "state": "AM",
            "address": "rua francy assis",
            "number": "2229",
            "postal_code": "69050750",
            "rating": 5,
            "role": "hairdresser",
            "cnpj": "12345678901212",
            "experience_years": 4,
            "resume": "ele é legal e joga bem",
            "preferences": json.dumps([]),
            'experience_time':'experience_time',
            'experiences':'experiences',
            'products':'products',
            'resume':'resume'
        }
        
        # Register and get hairdresser
        self.client.post(
            self.register_url,
            data=self.hairdresser_payload,
        )
        
        # Login
        login_payload = {
            'email': 'rodrigosc615@gmail.com',
            'password': 'Senha123'
        }
        self.client.post(
            self.login_url,
            data=json.dumps(login_payload),
            content_type='application/json'
        )
        
        # Get the hairdresser object
        self.hairdresser = Hairdresser.objects.get(user__email='rodrigosc615@gmail.com')
        
        # URL for creating multiple availabilities
        self.create_multiple_url = reverse('hairdresser_availabilities', kwargs={'hairdresser_id': self.hairdresser.id})
    
    def test_create_multiple_availability_success(self):
        # Payload with multiple availabilities
        payload = {
            'availabilities': [
                {
                    'weekday': 'monday',
                    'start_time': '09:00:00',
                    'end_time': '17:00:00'
                },
                {
                    'weekday': 'tuesday',
                    'start_time': '10:00:00',
                    'end_time': '18:00:00',
                    'break_start': '12:00:00',
                    'break_end': '13:00:00'
                }
            ]
        }
        
        # Create multiple availabilities
        response = self.client.post(
            self.create_multiple_url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Assertions
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Availability.objects.count(), 2)
        self.assertEqual(Availability.objects.filter(hairdresser=self.hairdresser).count(), 2)
    
    def test_create_multiple_availability_with_duplicate_weekday(self):
        # First create an availability for monday
        first_payload = {
            'availabilities': [
                {
                    'weekday': 'monday',
                    'start_time': '09:00:00',
                    'end_time': '17:00:00'
                }
            ]
        }
        
        self.client.post(
            self.create_multiple_url,
            data=json.dumps(first_payload),
            content_type='application/json'
        )
        
        # Try to create another availability for the same weekday
        second_payload = {
            'availabilities': [
                {
                    'weekday': 'monday',
                    'start_time': '10:00:00',
                    'end_time': '18:00:00'
                }
            ]
        }
        
        response = self.client.post(
            self.create_multiple_url,
            data=json.dumps(second_payload),
            content_type='application/json'
        )
        
        # Assertions
        assert_problem(response, 'availability-exists', detail='An availability already exists for this weekday.')
        self.assertEqual(Availability.objects.count(), 1)
    
    def test_create_multiple_availability_missing_fields(self):
        # Payload with missing required fields
        payload = {
            'availabilities': [
                {
                    'weekday': 'monday',
                    # Missing start_time and end_time
                }
            ]
        }
        
        response = self.client.post(
            self.create_multiple_url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Assertions
        assert_problem(response, 'validation-error', errors=[
            {'pointer': '#/availabilities/0/start_time', 'detail': 'This field is required.'},
            {'pointer': '#/availabilities/0/end_time', 'detail': 'This field is required.'},
        ])
        self.assertEqual(Availability.objects.count(), 0)
    
    def test_create_multiple_availability_invalid_weekday(self):
        # Payload with invalid weekday
        payload = {
            'availabilities': [
                {
                    'weekday': 'invalidday',
                    'start_time': '09:00:00',
                    'end_time': '17:00:00'
                }
            ]
        }
        
        response = self.client.post(
            self.create_multiple_url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Assertions
        assert_problem(response, 'validation-error', errors=[
            {'pointer': '#/availabilities/0/weekday', 'detail': 'The weekday must be one of monday to sunday.'},
        ])
        self.assertEqual(Availability.objects.count(), 0)
    
    def test_create_multiple_availability_nonexistent_hairdresser(self):
        # Try to create availability for a non-existent hairdresser
        non_existent_url = reverse('hairdresser_availabilities', kwargs={'hairdresser_id': 9999})
        
        payload = {
            'availabilities': [
                {
                    'weekday': 'monday',
                    'start_time': '09:00:00',
                    'end_time': '17:00:00'
                }
            ]
        }
        
        response = self.client.post(
            non_existent_url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # An id that is not the session hairdresser's is refused
        assert_problem(response, 'forbidden')
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
            "password": "Password123",
            "phone": "+5592984502890",
            "complement": "casa",
            "neighborhood": "centro",
            "city": "manaus",
            "state": "AM",
            "address": "Salon Street",
            "number": "123",
            "postal_code": "12345678",
            "rating": 5,
            "role": "hairdresser",
            "cnpj": "12345678901212",
            "experience_years": 5,
            "resume": "Professional hairdresser",
            "preferences": json.dumps([]),
            'experience_time':'experience_time',
            'experiences':'experiences',
            'products':'products',
            'resume':'resume'
        }
        
        # Register hairdresser
        self.client.post(
            self.register_url,
            data=self.hairdresser_payload,
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
        self.list_url = reverse('hairdresser_availabilities', args=[self.hairdresser.id])
        
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
        nonexistent_url = reverse('hairdresser_availabilities', args=[999])
        response = self.client.get(nonexistent_url)
        
        # The API should return an empty list rather than an error
        assert_problem(response, 'not-found', detail='Hairdresser not found.')


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
            "password": "Password123",
            "phone": "+5592984502890",
            "complement": "casa",
            "neighborhood": "centro",
            "city": "manaus",
            "state": "AM",
            "address": "Salon Street",
            "number": "123",
            "postal_code": "12345678",
            "rating": 5,
            "role": "hairdresser",
            "cnpj": "12345678901212",
            "experience_years": 5,
            "resume": "Professional hairdresser",
            "preferences": json.dumps([]),
            'experience_time':'experience_time',
            'experiences':'experiences',
            'products':'products',
            'resume':'resume'
        }
        
        # Register hairdresser
        self.client.post(
            self.register_url,
            data=self.hairdresser_payload,
        )
        
        self.client.post(
            self.login_url,
            data=json.dumps({'email': 'hairdresser@example.com', 'password': 'Password123'}),
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
        self.remove_url = reverse('availability_detail', args=[self.availability.id])
        
    def test_remove_availability_success(self):
        response = self.client.delete(self.remove_url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.content, b'')
        self.assertEqual(Availability.objects.count(), 0)
        
    def test_remove_nonexistent_availability(self):
        # Test with a non-existent availability ID
        nonexistent_url = reverse('availability_detail', args=[999])
        response = self.client.delete(nonexistent_url)
        
        assert_problem(response, 'not-found', detail='Availability not found.')
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
            "password": "Password123",
            "phone": "+5592984502890",
            "complement": "casa",
            "neighborhood": "centro",
            "city": "manaus",
            "state": "AM",
            "address": "Salon Street",
            "number": "123",
            "postal_code": "12345678",
            "rating": 5,
            "role": "hairdresser",
            "cnpj": "12345678901212",
            "experience_years": 5,
            "resume": "Professional hairdresser",
            "preferences": json.dumps([]),
            'experience_time':'experience_time',
            'experiences':'experiences',
            'products':'products',
            'resume':'resume'
        }
        
        # Register hairdresser
        self.client.post(
            self.register_url,
            data=self.hairdresser_payload,
        )
        
        self.client.post(
            self.login_url,
            data=json.dumps({'email': 'hairdresser@example.com', 'password': 'Password123'}),
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
        self.update_url = reverse('availability_detail', args=[self.availability.id])
        
    def test_update_availability_all_fields(self):
        response = self.client.patch(
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
        response = self.client.patch(
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
        nonexistent_url = reverse('availability_detail', args=[999])
        response = self.client.patch(
            nonexistent_url,
            data=json.dumps({
                'weekday': 'saturday',
                'start_time': '11:00:00',
                'end_time': '19:00:00'
            }),
            content_type='application/json'
        )
        
        assert_problem(response, 'not-found', detail='Availability not found.')
        
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

class UpdateMultipleAvailabilityTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('register')
        self.login_url = reverse('login')
        
        # Hairdresser payload
        self.hairdresser_payload = {
            "email": "rodrigosc615@gmail.com",
            "first_name": "Rodrigo Santos",
            "last_name": "o 12",
            "password": "Senha123",
            "phone": "+5592984502890",
            "complement": "casa",
            "neighborhood": "centro",
            "city": "manaus",
            "state": "AM",
            "address": "rua francy assis",
            "number": "2229",
            "postal_code": "69050750",
            "rating": 5,
            "role": "hairdresser",
            "cnpj": "12345678901212",
            "experience_years": 4,
            "resume": "ele é legal e joga bem",
            "preferences": json.dumps([]),
            'experience_time':'experience_time',
            'experiences':'experiences',
            'products':'products',
            'resume':'resume'
        }
        
        # Register and login hairdresser
        self.client.post(
            self.register_url,
            data=self.hairdresser_payload,
        )
        
        login_payload = {
            'email': 'rodrigosc615@gmail.com',
            'password': 'Senha123'
        }
        self.client.post(
            self.login_url,
            data=json.dumps(login_payload),
            content_type='application/json'
        )
        
        # Get the hairdresser object
        self.hairdresser = Hairdresser.objects.get(user__email='rodrigosc615@gmail.com')
        
        # Create existing availabilities
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
            end_time=time(18, 0),
            break_start=time(12, 0),
            break_end=time(13, 0)
        )
        
        # URL for updating multiple availabilities
        self.update_multiple_url = reverse('hairdresser_availabilities', kwargs={'hairdresser_id': self.hairdresser.id})
    
    def test_update_multiple_availability_success(self):
        """Test successful update of multiple availabilities - should replace all existing ones"""
        payload = {
            'availabilities': [
                {
                    'weekday': 'wednesday',
                    'start_time': '08:00:00',
                    'end_time': '16:00:00'
                },
                {
                    'weekday': 'thursday',
                    'start_time': '09:30:00',
                    'end_time': '17:30:00',
                    'break_start': '12:30:00',
                    'break_end': '13:30:00'
                },
                {
                    'weekday': 'friday',
                    'start_time': '10:00:00',
                    'end_time': '18:00:00'
                }
            ]
        }
        
        # Verify we start with 2 availabilities
        self.assertEqual(Availability.objects.filter(hairdresser=self.hairdresser).count(), 2)
        
        response = self.client.put(
            self.update_multiple_url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # Assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = json.loads(response.content)
        self.assertEqual(data['message'], 'Multiple availabilities registered successfully')
        
        # Should have 3 new availabilities (old ones deleted)
        self.assertEqual(Availability.objects.filter(hairdresser=self.hairdresser).count(), 3)
        
        # Verify old availabilities are gone
        self.assertFalse(Availability.objects.filter(hairdresser=self.hairdresser, weekday='monday').exists())
        self.assertFalse(Availability.objects.filter(hairdresser=self.hairdresser, weekday='tuesday').exists())
        
        # Verify new availabilities exist
        wednesday_availability = Availability.objects.get(hairdresser=self.hairdresser, weekday='wednesday')
        self.assertEqual(str(wednesday_availability.start_time), '08:00:00')
        self.assertEqual(str(wednesday_availability.end_time), '16:00:00')
        self.assertIsNone(wednesday_availability.break_start)
        self.assertIsNone(wednesday_availability.break_end)
        
        thursday_availability = Availability.objects.get(hairdresser=self.hairdresser, weekday='thursday')
        self.assertEqual(str(thursday_availability.start_time), '09:30:00')
        self.assertEqual(str(thursday_availability.end_time), '17:30:00')
        self.assertEqual(str(thursday_availability.break_start), '12:30:00')
        self.assertEqual(str(thursday_availability.break_end), '13:30:00')
        
        friday_availability = Availability.objects.get(hairdresser=self.hairdresser, weekday='friday')
        self.assertEqual(str(friday_availability.start_time), '10:00:00')
        self.assertEqual(str(friday_availability.end_time), '18:00:00')
    
    def test_update_multiple_availability_with_break_times(self):
        """Test update with break times only"""
        payload = {
            'availabilities': [
                {
                    'weekday': 'saturday',
                    'start_time': '09:00:00',
                    'end_time': '17:00:00',
                    'break_start': '12:00:00',
                    'break_end': '13:00:00'
                }
            ]
        }
        
        response = self.client.put(
            self.update_multiple_url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Availability.objects.filter(hairdresser=self.hairdresser).count(), 1)
        
        availability = Availability.objects.get(hairdresser=self.hairdresser, weekday='saturday')
        self.assertEqual(str(availability.break_start), '12:00:00')
        self.assertEqual(str(availability.break_end), '13:00:00')
    
    def test_update_multiple_availability_without_break_times(self):
        """Test update without break times"""
        payload = {
            'availabilities': [
                {
                    'weekday': 'sunday',
                    'start_time': '10:00:00',
                    'end_time': '16:00:00'
                }
            ]
        }
        
        response = self.client.put(
            self.update_multiple_url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Availability.objects.filter(hairdresser=self.hairdresser).count(), 1)
        
        availability = Availability.objects.get(hairdresser=self.hairdresser, weekday='sunday')
        self.assertIsNone(availability.break_start)
        self.assertIsNone(availability.break_end)
    
    def test_update_multiple_availability_missing_weekday(self):
        """Test update with missing weekday field"""
        payload = {
            'availabilities': [
                {
                    'start_time': '09:00:00',
                    'end_time': '17:00:00'
                }
            ]
        }
        
        response = self.client.put(
            self.update_multiple_url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert_problem(response, 'validation-error', errors=[
            {'pointer': '#/availabilities/0/weekday', 'detail': 'This field is required.'},
        ])
    
    def test_update_multiple_availability_missing_start_time(self):
        """Test update with missing start_time field"""
        payload = {
            'availabilities': [
                {
                    'weekday': 'monday',
                    'end_time': '17:00:00'
                }
            ]
        }
        
        response = self.client.put(
            self.update_multiple_url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert_problem(response, 'validation-error', errors=[
            {'pointer': '#/availabilities/0/start_time', 'detail': 'This field is required.'},
        ])
    
    def test_update_multiple_availability_missing_end_time(self):
        """Test update with missing end_time field"""
        payload = {
            'availabilities': [
                {
                    'weekday': 'monday',
                    'start_time': '09:00:00'
                }
            ]
        }
        
        response = self.client.put(
            self.update_multiple_url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert_problem(response, 'validation-error', errors=[
            {'pointer': '#/availabilities/0/end_time', 'detail': 'This field is required.'},
        ])
    
    def test_update_multiple_availability_invalid_weekday(self):
        """Test update with invalid weekday"""
        payload = {
            'availabilities': [
                {
                    'weekday': 'invalidday',
                    'start_time': '09:00:00',
                    'end_time': '17:00:00'
                }
            ]
        }
        
        response = self.client.put(
            self.update_multiple_url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert_problem(response, 'validation-error', errors=[
            {'pointer': '#/availabilities/0/weekday', 'detail': 'The weekday must be one of monday to sunday.'},
        ])
    
    def test_update_multiple_availability_nonexistent_hairdresser(self):
        """Test update for non-existent hairdresser"""
        non_existent_url = reverse('hairdresser_availabilities', kwargs={'hairdresser_id': 9999})
        
        payload = {
            'availabilities': [
                {
                    'weekday': 'monday',
                    'start_time': '09:00:00',
                    'end_time': '17:00:00'
                }
            ]
        }
        
        response = self.client.put(
            non_existent_url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # An id that is not the session hairdresser's is refused, and nothing is deleted
        assert_problem(response, 'forbidden')
        self.assertEqual(Availability.objects.filter(hairdresser=self.hairdresser).count(), 2)
    
    def test_update_multiple_availability_empty_list(self):
        """Test update with empty availabilities list"""
        payload = {
            'availabilities': []
        }
        
        response = self.client.put(
            self.update_multiple_url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # All existing availabilities should be deleted
        self.assertEqual(Availability.objects.filter(hairdresser=self.hairdresser).count(), 0)
    
    def test_update_multiple_availability_duplicate_weekdays_in_payload(self):
        """Test update with duplicate weekdays in the same payload"""
        payload = {
            'availabilities': [
                {
                    'weekday': 'monday',
                    'start_time': '09:00:00',
                    'end_time': '17:00:00'
                },
                {
                    'weekday': 'monday',
                    'start_time': '10:00:00',
                    'end_time': '18:00:00'
                }
            ]
        }
        
        response = self.client.put(
            self.update_multiple_url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        # This should fail because of duplicate weekdays
        assert_problem(response, 'availability-exists', detail='An availability already exists for this weekday.')
    
    def test_update_multiple_availability_malformed_json(self):
        """Test update with malformed JSON"""
        response = self.client.put(
            self.update_multiple_url,
            data='invalid json',
            content_type='application/json'
        )
        
        assert_problem(response, 'malformed-request')
    
    def test_update_multiple_availability_missing_availabilities_key(self):
        """Test update with missing 'availabilities' key in payload"""
        payload = {
            'invalid_key': []
        }
        
        response = self.client.put(
            self.update_multiple_url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        assert_problem(response, 'validation-error', errors=[
            {'pointer': '#/availabilities', 'detail': 'This field is required.'},
        ])
    
    def test_update_multiple_availability_partial_break_time(self):
        """Test update with only break_start or break_end (not both)"""
        payload = {
            'availabilities': [
                {
                    'weekday': 'monday',
                    'start_time': '09:00:00',
                    'end_time': '17:00:00',
                    'break_start': '12:00:00'
                    # Missing break_end
                }
            ]
        }
        
        response = self.client.put(
            self.update_multiple_url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should create availability without break times
        availability = Availability.objects.get(hairdresser=self.hairdresser, weekday='monday')
        self.assertIsNone(availability.break_start)
        self.assertIsNone(availability.break_end)
    
    def test_update_multiple_availability_replaces_all_existing(self):
        """Test that update replaces ALL existing availabilities, not just the ones with matching weekdays"""
        # Start with 2 existing availabilities (monday, tuesday)
        initial_count = Availability.objects.filter(hairdresser=self.hairdresser).count()
        self.assertEqual(initial_count, 2)
        
        # Update with completely different weekdays
        payload = {
            'availabilities': [
                {
                    'weekday': 'wednesday',
                    'start_time': '08:00:00',
                    'end_time': '16:00:00'
                },
                {
                    'weekday': 'saturday',
                    'start_time': '10:00:00',
                    'end_time': '14:00:00'
                }
            ]
        }
        
        response = self.client.put(
            self.update_multiple_url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Should have exactly 2 availabilities (the new ones)
        self.assertEqual(Availability.objects.filter(hairdresser=self.hairdresser).count(), 2)
        
        # Old availabilities should be gone
        self.assertFalse(Availability.objects.filter(hairdresser=self.hairdresser, weekday='monday').exists())
        self.assertFalse(Availability.objects.filter(hairdresser=self.hairdresser, weekday='tuesday').exists())
        
        # New availabilities should exist
        self.assertTrue(Availability.objects.filter(hairdresser=self.hairdresser, weekday='wednesday').exists())
        self.assertTrue(Availability.objects.filter(hairdresser=self.hairdresser, weekday='saturday').exists())

class AvailabilityOwnershipTest(TestCase):
    """Every write endpoint requires a session of the hairdresser who owns the schedule."""

    def setUp(self):
        self.client = APIClient()
        self.fake = get_cognito().client
        self.owner = self._hairdresser('owner@example.com', 'sub-owner', '5592999990001')
        self.intruder = self._hairdresser('intruder@example.com', 'sub-intruder', '5592999990002')
        self.availability = Availability.objects.create(
            hairdresser=self.owner, weekday='monday', start_time=time(9, 0), end_time=time(17, 0)
        )
        self.schedule = json.dumps({'availabilities': [
            {'weekday': 'sunday', 'start_time': '01:00:00', 'end_time': '02:00:00'}
        ]})

    def _hairdresser(self, email, sub, phone):
        user = User.objects.create(
            first_name='Ana', last_name='Silva', phone=phone, neighborhood='Centro', city='Manaus',
            state='AM', address='Rua A', postal_code='69000000', email=email, role='hairdresser',
            cognito_sub=sub,
        )
        return Hairdresser.objects.create(user=user, cnpj='12345678901212')

    def _requests(self):
        return {
            'create multiple': lambda: self.client.post(
                reverse('hairdresser_availabilities', args=[self.owner.id]),
                data=self.schedule, content_type='application/json'),
            'update multiple': lambda: self.client.put(
                reverse('hairdresser_availabilities', args=[self.owner.id]),
                data=self.schedule, content_type='application/json'),
            'update': lambda: self.client.patch(
                reverse('availability_detail', args=[self.availability.id]),
                data=json.dumps({'start_time': '01:00:00'}), content_type='application/json'),
            'remove': lambda: self.client.delete(reverse('availability_detail', args=[self.availability.id])),
        }

    def _assert_schedule_untouched(self):
        self.assertEqual(list(Availability.objects.values_list('id', flat=True)), [self.availability.id])
        self.availability.refresh_from_db()
        self.assertEqual(self.availability.start_time, time(9, 0))

    def test_without_session_every_write_is_refused_with_401(self):
        for name, send in self._requests().items():
            with self.subTest(endpoint=name):
                response = send()
                assert_problem(response, 'invalid-session')
                self._assert_schedule_untouched()

    def test_another_hairdresser_is_refused_with_403(self):
        self.client.cookies['jwt'] = self.fake.make_access_token('sub-intruder')

        for name, send in self._requests().items():
            with self.subTest(endpoint=name):
                response = send()
                assert_problem(response, 'forbidden')
                self._assert_schedule_untouched()

    def test_owner_replaces_own_schedule(self):
        self.client.cookies['jwt'] = self.fake.make_access_token('sub-owner')

        response = self._requests()['update multiple']()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        created = Availability.objects.get()
        self.assertEqual((created.hairdresser, created.weekday), (self.owner, 'sunday'))


class AvailabilityProblemsTest(TestCase):
    """Every error of the availability endpoints is a problem+json that points at what is wrong."""

    def setUp(self):
        self.client = APIClient()
        self.fake = get_cognito().client
        self.user = User.objects.create(
            first_name='Ana', last_name='Silva', phone='5592999990000', neighborhood='Centro', city='Manaus',
            state='AM', address='Rua A', postal_code='69000000', email='ana@example.com', role='hairdresser',
            cognito_sub='sub-owner',
        )
        self.hairdresser = Hairdresser.objects.create(user=self.user, cnpj='12345678901212')
        self.client.cookies['jwt'] = self.fake.make_access_token('sub-owner')
        self.create_url = reverse('create_availability')
        self.create_multiple_url = reverse('hairdresser_availabilities', args=[self.hairdresser.id])
        self.update_multiple_url = reverse('hairdresser_availabilities', args=[self.hairdresser.id])
        self.monday = {'weekday': 'monday', 'start_time': '09:00:00', 'end_time': '17:00:00'}

    def _send(self, method, url, body):
        if not isinstance(body, str):
            body = json.dumps(body)
        return getattr(self.client, method)(url, data=body, content_type='application/json')

    def test_a_customer_creating_an_availability_is_refused_with_403_hairdresser_required(self):
        customer = User.objects.create(
            first_name='Cli', last_name='Ente', phone='5592999990001', neighborhood='Centro', city='Manaus',
            state='AM', address='Rua B', postal_code='69000000', email='cli@example.com', role='customer',
            cognito_sub='sub-customer',
        )
        Customer.objects.create(user=customer, cpf='12345678901')
        self.client.cookies['jwt'] = self.fake.make_access_token('sub-customer')

        response = self._send('post', self.create_url, self.monday)

        assert_problem(response, 'hairdresser-required', detail='Only hairdressers can perform this action.')
        self.assertEqual(Availability.objects.count(), 0)

    def test_creating_with_no_fields_reports_the_three_required_ones(self):
        response = self._send('post', self.create_url, {})

        assert_problem(response, 'validation-error', errors=[
            {'pointer': '#/weekday', 'detail': 'This field is required.'},
            {'pointer': '#/start_time', 'detail': 'This field is required.'},
            {'pointer': '#/end_time', 'detail': 'This field is required.'},
        ])

    def test_creating_with_an_invalid_weekday_points_at_it(self):
        response = self._send('post', self.create_url, {**self.monday, 'weekday': 'funday'})

        assert_problem(response, 'validation-error', errors=[
            {'pointer': '#/weekday', 'detail': 'The weekday must be one of monday to sunday.'},
        ])

    def test_creating_with_times_that_are_not_hh_mm_points_at_each_one(self):
        for bad in ('nine', '25:99:00', 900):
            with self.subTest(bad=bad):
                response = self._send('post', self.create_url, {**self.monday, 'start_time': bad, 'break_end': bad})

                assert_problem(response, 'validation-error', errors=[
                    {'pointer': '#/start_time', 'detail': 'The time must be in HH:MM format.'},
                    {'pointer': '#/break_end', 'detail': 'The time must be in HH:MM format.'},
                ])
        self.assertEqual(Availability.objects.count(), 0)

    def test_creating_the_same_weekday_twice_answers_409(self):
        self._send('post', self.create_url, self.monday)

        response = self._send('post', self.create_url, {**self.monday, 'start_time': '10:00:00'})

        assert_problem(response, 'availability-exists', detail='An availability already exists for this weekday.')
        self.assertEqual(Availability.objects.count(), 1)

    def test_creating_with_a_body_that_is_not_json_answers_400(self):
        for raw in ('{nope', '[1]'):
            with self.subTest(raw=raw):
                assert_problem(self._send('post', self.create_url, raw), 'malformed-request')

    def test_creating_with_hh_mm_times_and_a_break_works(self):
        body = {**self.monday, 'start_time': '09:00', 'end_time': '17:30', 'break_start': '12:00', 'break_end': '13:00'}

        response = self._send('post', self.create_url, body)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Availability.objects.get()
        self.assertEqual((created.break_start, created.break_end), (time(12, 0), time(13, 0)))

    def test_bulk_create_reports_the_errors_of_every_item_before_writing_any(self):
        body = {'availabilities': [
            self.monday,
            {'weekday': 'tuesday'},
            {**self.monday, 'weekday': 'someday'},
        ]}

        response = self._send('post', self.create_multiple_url, body)

        assert_problem(response, 'validation-error', errors=[
            {'pointer': '#/availabilities/1/start_time', 'detail': 'This field is required.'},
            {'pointer': '#/availabilities/1/end_time', 'detail': 'This field is required.'},
            {'pointer': '#/availabilities/2/weekday', 'detail': 'The weekday must be one of monday to sunday.'},
        ])
        self.assertEqual(Availability.objects.count(), 0)

    def test_bulk_create_needs_a_list_of_objects(self):
        cases = [
            ({'availabilities': 'monday'}, [{'pointer': '#/availabilities', 'detail': 'This field must be a list.'}]),
            ({'availabilities': [self.monday, 5]},
             [{'pointer': '#/availabilities/1', 'detail': 'Each item must be an object.'}]),
            ({}, [{'pointer': '#/availabilities', 'detail': 'This field is required.'}]),
        ]
        for body, errors in cases:
            with self.subTest(body=body):
                assert_problem(self._send('post', self.create_multiple_url, body), 'validation-error', errors=errors)
        self.assertEqual(Availability.objects.count(), 0)

    def test_bulk_create_with_a_body_that_is_not_json_answers_400(self):
        assert_problem(self._send('post', self.create_multiple_url, '{nope'), 'malformed-request')

    def test_bulk_create_of_an_existing_weekday_answers_409(self):
        Availability.objects.create(hairdresser=self.hairdresser, weekday='monday',
                                    start_time=time(8, 0), end_time=time(12, 0))

        response = self._send('post', self.create_multiple_url, {'availabilities': [self.monday]})

        assert_problem(response, 'availability-exists')

    def test_bulk_update_with_an_invalid_item_keeps_the_current_schedule(self):
        Availability.objects.create(hairdresser=self.hairdresser, weekday='friday',
                                    start_time=time(8, 0), end_time=time(12, 0))

        response = self._send('put', self.update_multiple_url, {'availabilities': [{'weekday': 'monday'}]})

        assert_problem(response, 'validation-error')
        self.assertEqual(list(Availability.objects.values_list('weekday', flat=True)), ['friday'])

    def test_bulk_update_answers_200_and_replaces_the_schedule(self):
        Availability.objects.create(hairdresser=self.hairdresser, weekday='friday',
                                    start_time=time(8, 0), end_time=time(12, 0))

        response = self._send('put', self.update_multiple_url, {'availabilities': [self.monday]})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(list(Availability.objects.values_list('weekday', flat=True)), ['monday'])

    def test_bulk_update_that_cannot_delete_the_schedule_answers_500(self):
        with patch('availability.views.delete_all_availabilities_by_hairdresser_safe', return_value=False):
            response = self._send('put', self.update_multiple_url, {'availabilities': [self.monday]})

        assert_problem(response, 'internal-error', detail='The current availabilities could not be replaced.')

    def test_updating_one_availability_validates_the_fields_it_receives(self):
        availability = Availability.objects.create(hairdresser=self.hairdresser, weekday='friday',
                                                   start_time=time(8, 0), end_time=time(12, 0))
        url = reverse('availability_detail', args=[availability.id])

        response = self._send('patch', url, {'weekday': 'someday', 'end_time': 'noon'})

        assert_problem(response, 'validation-error', errors=[
            {'pointer': '#/weekday', 'detail': 'The weekday must be one of monday to sunday.'},
            {'pointer': '#/end_time', 'detail': 'The time must be in HH:MM format.'},
        ])
        availability.refresh_from_db()
        self.assertEqual((availability.weekday, availability.end_time), ('friday', time(12, 0)))

    def test_updating_one_availability_with_a_body_that_is_not_json_answers_400(self):
        availability = Availability.objects.create(hairdresser=self.hairdresser, weekday='friday',
                                                   start_time=time(8, 0), end_time=time(12, 0))

        response = self._send('patch', reverse('availability_detail', args=[availability.id]), '{nope')

        assert_problem(response, 'malformed-request')

    def test_listing_answers_500_without_the_exception_text_when_the_read_fails(self):
        with patch('availability.views.get_hairdresser_availability', return_value={'error': 'db is down'}):
            with self.assertLogs('availability.views', level='ERROR'):
                response = self.client.get(reverse('hairdresser_availabilities', args=[self.hairdresser.id]))

        body = assert_problem(response, 'internal-error', detail='The availabilities could not be listed.')
        self.assertNotIn('db is down', json.dumps(body))
