from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
import json
from datetime import datetime, timedelta
from django.utils import timezone

from users.models import User, Customer, Hairdresser
from service.models import Service
from reserve.models import Reserve
from agenda.models import Agenda
from availability.models import Availability


class ReserveTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # URLs
        self.create_url = reverse('create_reserve')
        self.list_url = reverse('list_reserve')
        self.remove_url = lambda reserve_id: reverse('remove_reserve', args=[reserve_id])
        self.get_slots_url = lambda hairdresser_id: reverse('get_slots', args=[hairdresser_id])
        
        # Create test user (customer)
        self.customer_user = User.objects.create(
            email="customer@example.com",
            password="customer123",
            first_name="Test",
            last_name="Customer",
            phone="+5592984501111",
            complement="Apt 101",
            neighborhood="Downtown",
            city="Manaus",
            state="AM",
            address="Customer Street",
            number="123",
            postal_code="69050750",
            role="customer"
        )
        
        self.customer = Customer.objects.create(
            user=self.customer_user,
            cpf="12345678901"
        )
        
        # Create test user (hairdresser)
        self.hairdresser_user = User.objects.create(
            email="hairdresser@example.com",
            password="hairdresser123",
            first_name="Test",
            last_name="Hairdresser",
            phone="+5592984502222",
            complement="Apt 102",
            neighborhood="Downtown",
            city="Manaus",
            state="AM",
            address="Hairdresser Street",
            number="456",
            postal_code="69050750",
            role="hairdresser"
        )
        
        self.hairdresser = Hairdresser.objects.create(
            user=self.hairdresser_user,
            cnpj="12345678901212",
            experience_years=4,
            resume= "ele é legal e joga bem"
        )
        
        # Create test service
        self.service = Service.objects.create(
            name="Haircut",
            description="Basic haircut service",
            price=50.00,
            duration=60,  # 60 minutes
            hairdresser = self.hairdresser
        )
        
        # Create test availability for hairdresser
        self.availability = Availability.objects.create(
            hairdresser=self.hairdresser,
            weekday="monday",
            start_time=timezone.datetime.strptime("09:00", "%H:%M").time(),
            end_time=timezone.datetime.strptime("17:00", "%H:%M").time(),
            break_start=timezone.datetime.strptime("12:00", "%H:%M").time(),
            break_end=timezone.datetime.strptime("13:00", "%H:%M").time()
        )
        
        # Create a test reserve and agenda
        self.reserve_start_time = timezone.now() + timedelta(days=1)
        self.reserve_start_time = self.reserve_start_time.replace(hour=10, minute=0, second=0, microsecond=0)
        
        self.reserve = Reserve.objects.create(
            start_time=self.reserve_start_time,
            customer=self.customer,
            service=self.service
        )
        
        self.agenda = Agenda.objects.create(
            start_time=self.reserve_start_time,
            end_time=self.reserve_start_time + timedelta(minutes=self.service.duration),
            hairdresser=self.hairdresser,
            service=self.service
        )


class CreateReserveTest(ReserveTestCase):
    def test_create_reserve_success(self):
        """Test successful reserve creation"""
        # Create a new start time that doesn't conflict with the existing reserve
        new_start_time = self.reserve_start_time + timedelta(hours=2)
        
        reserve_data = {
            'start_time': new_start_time.isoformat(),
            'customer': self.customer.id,
            'hairdresser': self.hairdresser.id,
            'service': self.service.id
        }
        
        # Assuming 'create-reserve' is the name of your URL pattern
        response = self.client.post(
            self.create_url,
            data=json.dumps(reserve_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Reserve.objects.count(), 2)  # 1 from setup + 1 new
        self.assertEqual(Agenda.objects.count(), 2)   # 1 from setup + 1 new
        
    def test_create_reserve_overlap_error(self):
        """Test reserve creation with an overlapping start time"""
        reserve_data = {
            'start_time': self.reserve_start_time.isoformat(),  # Same start time as existing reserve
            'customer': self.customer.id,
            'hairdresser': self.hairdresser.id,
            'service': self.service.id
        }
        
        response = self.client.post(
            self.create_url,
            data=json.dumps(reserve_data),
            content_type='application/json'
        )
        
        # --- FIX: Assert the correct error message and status code ---
        # The code now returns a 409 Conflict for this specific error.
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        # Check for the actual user-facing error message from the view logic.
        self.assertEqual(response.json()['error'], 'Desculpe, este horário foi agendado por outra pessoa. Por favor, escolha outro.')
        self.assertEqual(Reserve.objects.count(), 1)  # No new reserve should be created
        self.assertEqual(Agenda.objects.count(), 1)   # No new agenda item should be created
        
    def test_create_reserve_invalid_customer(self):
        """Test reserve creation with non-existent customer"""
        new_start_time = self.reserve_start_time + timedelta(hours=2)
        
        reserve_data = {
            'start_time': new_start_time.isoformat(),
            'customer': 9999,  # Non-existent ID
            'hairdresser': self.hairdresser.id,
            'service': self.service.id
        }
        
        response = self.client.post(
            self.create_url,
            data=json.dumps(reserve_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['error'], 'Customer not found')
        
    def test_create_reserve_invalid_hairdresser(self):
        """Test reserve creation with non-existent hairdresser"""
        new_start_time = self.reserve_start_time + timedelta(hours=2)
        
        reserve_data = {
            'start_time': new_start_time.isoformat(),
            'customer': self.customer.id,
            'hairdresser': 9999,  # Non-existent ID
            'service': self.service.id
        }
        
        response = self.client.post(
            self.create_url,
            data=json.dumps(reserve_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['error'], 'Hairdresser not found')
        
    def test_create_reserve_invalid_service(self):
        """Test reserve creation with a non-existent service"""
        new_start_time = self.reserve_start_time + timedelta(hours=2)
        
        reserve_data = {
            'start_time': new_start_time.isoformat(),
            'customer': self.customer.id,
            'hairdresser': self.hairdresser.id,
            'service': 9999  # Non-existent ID
        }
        
        response = self.client.post(
            self.create_url,
            data=json.dumps(reserve_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['error'], 'Service not found')


class ListReserveTest(ReserveTestCase):
    def test_list_all_reserves(self):
        """Test listing all reserves"""
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()['data']), 1)
        
    def test_list_user_reserves(self):
        """Test listing reserves for a specific user"""
        
        # Create a list_user_url with the customer's user ID
        list_user_url = reverse('list_reserve', args=[self.customer.id])
        
        response = self.client.get(list_user_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class RemoveReserveTest(ReserveTestCase):
    def test_remove_reserve_success(self):
        """Test successful reserve removal"""
        response = self.client.delete(self.remove_url(self.reserve.id))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['data'], 'reserve deleted successfully')
        self.assertEqual(Reserve.objects.count(), 0)
        
    def test_remove_nonexistent_reserve(self):
        """Test removing a non-existent reserve"""
        
        response = self.client.delete(self.remove_url(9999))  # Non-existent ID
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ReserveSlotTest(ReserveTestCase):
    def test_get_available_slots(self):
        """Test getting available time slots for a hairdresser"""
        # Get tomorrow's date which is a Monday (to match our test availability)
        today = timezone.now().date()
        days_ahead = 7 - today.weekday()  # Next Monday
        next_monday = today + timedelta(days=days_ahead)
        
        slot_data = {
            'date': next_monday.strftime('%Y-%m-%d'),
            'service': self.service.id
        }
        
        response = self.client.post(
            self.get_slots_url(self.hairdresser.id),
            data=json.dumps(slot_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('available_slots', response.json())
        # The number of slots depends on service duration and availability
        # For a 60-minute service, 9am-5pm with 1hr lunch break,
        # we expect approximately 14 half-hour slots
        # This might need adjustment based on exact business logic
        
    def test_get_slots_invalid_hairdresser(self):
        """Test getting slots for non-existent hairdresser"""
        today = timezone.now().date()
        
        slot_data = {
            'date': today.strftime('%Y-%m-%d'),
            'service': self.service.id
        }
        
        response = self.client.post(
            self.get_slots_url(9999),  # Non-existent ID
            data=json.dumps(slot_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['error'], 'Hairdresser not found')
        
    def test_get_slots_invalid_service(self):
        """Test getting slots with non-existent service"""
        today = timezone.now().date()
        
        slot_data = {
            'date': today.strftime('%Y-%m-%d'),
            'service': 9999  # Non-existent ID
        }
        
        response = self.client.post(
            self.get_slots_url(self.hairdresser.id),
            data=json.dumps(slot_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.json()['error'], 'Service not found')
        
    def test_get_slots_invalid_date_format(self):
        """Test getting slots with invalid date format"""
        slot_data = {
            'date': 'invalid-date',
            'service': self.service.id
        }
        
        response = self.client.post(
            self.get_slots_url(self.hairdresser.id),
            data=json.dumps(slot_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()['error'], 'Invalid date format')
        
    def test_get_slots_no_availability(self):
        """Test getting slots when hairdresser has no availability for that day"""
        # Create a date for Tuesday, when we have no availability set
        today = timezone.now().date()
        days_ahead = (1 - today.weekday()) % 7 + 1  # Next Tuesday
        next_tuesday = today + timedelta(days=days_ahead)
        
        slot_data = {
            'date': next_tuesday.strftime('%Y-%m-%d'),
            'service': self.service.id
        }
        
        response = self.client.post(
            self.get_slots_url(self.hairdresser.id),
            data=json.dumps(slot_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['available_slots'], [])