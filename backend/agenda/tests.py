from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
import json
from datetime import datetime, timedelta
from django.utils import timezone

from users.models import User, Hairdresser
from service.models import Service
from agenda.models import Agenda


class AgendaTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # URLs
        self.create_url = reverse('create_agenda')
        self.list_url = reverse('list_agenda')
        self.remove_url = lambda agenda_id: reverse('remove_agenda', args=[agenda_id])
        
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
            role="hairdresser",
            rating=4.5
        )
        
        self.hairdresser = Hairdresser.objects.create(
            user=self.hairdresser_user,
            cnpj="12345678901212",
            experience_years=4,
            resume= "ele é legal e joga bem"
        )
        
        # Create another hairdresser for testing
        self.hairdresser_user2 = User.objects.create(
            email="hairdresser2@example.com",
            password="hairdresser123",
            first_name="Test2",
            last_name="Hairdresser2",
            phone="+5592984503333",
            complement="Apt 103",
            neighborhood="Downtown",
            city="Manaus",
            state="AM",
            address="Hairdresser Street",
            number="789",
            postal_code="69050750",
            role="hairdresser",
            rating=4.0
        )
        
        self.hairdresser2 = Hairdresser.objects.create(
            user=self.hairdresser_user2,
            cnpj="12345678901245",
            experience_years=4,
            resume= "ele é legal e joga bem2"
        )
        
        # Create test service
        self.service = Service.objects.create(
            name="Haircut",
            description="Basic haircut service",
            price=50.00,
            duration=60,  # 60 minutes
            hairdresser=self.hairdresser
        )
        
        # Create a test agenda
        self.agenda_start_time = timezone.now() + timedelta(days=1)
        self.agenda_start_time = self.agenda_start_time.replace(hour=10, minute=0, second=0, microsecond=0)
        self.agenda_end_time = self.agenda_start_time + timedelta(minutes=self.service.duration)
        
        self.agenda = Agenda.objects.create(
            start_time=self.agenda_start_time,
            end_time=self.agenda_end_time,
            hairdresser=self.hairdresser,
            service=self.service
        )


class CreateAgendaTest(AgendaTestCase):
    def test_create_agenda_success(self):
        """Test successful agenda creation"""
        # Create new start and end times
        new_start_time = self.agenda_start_time + timedelta(hours=2)
        new_end_time = new_start_time + timedelta(minutes=self.service.duration)
        
        agenda_data = {
            'start_time': new_start_time.isoformat(),
            'end_time': new_end_time.isoformat(),
            'hairdresser': self.hairdresser.id,
            'service': self.service.id
        }
        
        response = self.client.post(
            self.create_url,
            data=json.dumps(agenda_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()['message'], 'Agenda register created successfully')
        self.assertEqual(Agenda.objects.count(), 2)  # 1 from setup + 1 new
        
    def test_create_agenda_invalid_hairdresser(self):
        """Test agenda creation with non-existent hairdresser"""
        new_start_time = self.agenda_start_time + timedelta(hours=2)
        new_end_time = new_start_time + timedelta(minutes=self.service.duration)
        
        agenda_data = {
            'start_time': new_start_time.isoformat(),
            'end_time': new_end_time.isoformat(),
            'hairdresser': 9999,  # Non-existent ID
            'service': self.service.id
        }
        
        response = self.client.post(
            self.create_url,
            data=json.dumps(agenda_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.json()['error'], 'Hairdresser not found')
        
    def test_create_agenda_invalid_service(self):
        """Test agenda creation with non-existent service"""
        new_start_time = self.agenda_start_time + timedelta(hours=2)
        new_end_time = new_start_time + timedelta(minutes=self.service.duration)
        
        agenda_data = {
            'start_time': new_start_time.isoformat(),
            'end_time': new_end_time.isoformat(),
            'hairdresser': self.hairdresser.id,
            'service': 9999  # Non-existent ID
        }
        
        response = self.client.post(
            self.create_url,
            data=json.dumps(agenda_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.json()['error'], 'Service not found')
        
    def test_create_agenda_field_name_mismatch(self):
        """Test the field name bug in CreateAgenda view (Hairdresser vs hairdresser)"""
        
        new_start_time = self.agenda_start_time + timedelta(hours=2)
        new_end_time = new_start_time + timedelta(minutes=self.service.duration)
        
        agenda_data = {
            'start_time': new_start_time.isoformat(),
            'end_time': new_end_time.isoformat(),
            'hairdresser': self.hairdresser.id,
            'service': self.service.id
        }
        
        response = self.client.post(
            self.create_url,
            data=json.dumps(agenda_data),
            content_type='application/json'
        )
        
        # This will fail with an exception due to field mismatch
        # After fixing, it should return HTTP 201
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


class ListAgendaTest(AgendaTestCase):
    def test_list_all_agendas(self):
        """Test listing all agendas"""
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()['data']), 1)
        
    def test_list_hairdresser_agendas(self):
        """Test listing agendas for a specific hairdresser"""
        # Create another agenda for a different hairdresser
        Agenda.objects.create(
            start_time=self.agenda_start_time,
            end_time=self.agenda_end_time,
            hairdresser=self.hairdresser2,
            service=self.service
        )
        
        # Create a list_hairdresser_url with the hairdresser's ID
        list_hairdresser_url = reverse('list_agenda', args=[self.hairdresser.id])
        
        response = self.client.get(list_hairdresser_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()['data']), 1)
        
    def test_list_nonexistent_hairdresser_agendas(self):
        """Test listing agendas for a non-existent hairdresser"""
        list_hairdresser_url = reverse('list_agenda', args=[9999])  # Non-existent ID
        response = self.client.get(list_hairdresser_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

class RemoveAgendaTest(AgendaTestCase):
    def test_remove_agenda_success(self):
        """Test successful agenda removal"""
        response = self.client.delete(self.remove_url(self.agenda.id))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['data'], 'Agenda register deleted successfully')
        self.assertEqual(Agenda.objects.count(), 0)
        
    def test_remove_nonexistent_agenda(self):
        """Test removing a non-existent agenda"""        
        response = self.client.delete(self.remove_url(9999))  # Non-existent ID
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)