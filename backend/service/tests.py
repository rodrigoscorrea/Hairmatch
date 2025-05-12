from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
import json
from decimal import Decimal

from users.models import User, Hairdresser
from service.models import Service


class ServiceTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # URLs
        self.create_url = reverse('create_service')
        self.list_url = reverse('list_service')
        self.list_service_url = lambda service_id: reverse('list_service', args=[service_id])
        self.update_url = lambda service_id: reverse('update_service', args=[service_id])
        self.remove_url = lambda service_id: reverse('remove_service', args=[service_id])
        
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
            rating=3.0
        )
        
        self.hairdresser2 = Hairdresser.objects.create(
            user=self.hairdresser_user2,
            cnpj="12345678901567",
            experience_years=3,
            resume= "ele é legal e joga bem2"
        )
        
        # Create a test service
        self.service = Service.objects.create(
            name="Haircut",
            description="Basic haircut service",
            price=Decimal('50.00'),
            duration=60,  # 60 minutes
            hairdresser=self.hairdresser
        )
        
        # Create another service for the second hairdresser
        self.service2 = Service.objects.create(
            name="Hair Coloring",
            description="Hair coloring service",
            price=Decimal('120.00'),
            duration=120,  # 120 minutes
            hairdresser=self.hairdresser2
        )

class CreateServiceTest(ServiceTestCase):
    def test_create_service_success(self):
        """Test successful service creation"""
        service_data = {
            'name': 'Hair Styling',
            'description': 'Professional hair styling service',
            'price': '75.00',
            'duration': 45,
            'hairdresser': self.hairdresser.id
        }
        
        response = self.client.post(
            self.create_url,
            data=json.dumps(service_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()['message'], 'Service created successfully')
        self.assertEqual(Service.objects.count(), 3)  # 2 from setup + 1 new
        
        # Verify the service was created correctly
        new_service = Service.objects.get(name='Hair Styling')
        self.assertEqual(new_service.description, 'Professional hair styling service')
        self.assertEqual(new_service.price, Decimal('75.00'))
        self.assertEqual(new_service.duration, 45)
        self.assertEqual(new_service.hairdresser, self.hairdresser)
        
    def test_create_service_invalid_hairdresser(self):
        """Test service creation with non-existent hairdresser"""
        service_data = {
            'name': 'Hair Styling',
            'description': 'Professional hair styling service',
            'price': '75.00',
            'duration': 45,
            'hairdresser': 9999  # Non-existent ID
        }
        
        response = self.client.post(
            self.create_url,
            data=json.dumps(service_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.json()['error'], 'Hairdresser not found')
        self.assertEqual(Service.objects.count(), 2)  # No new service created
        
    def test_create_service_missing_required_fields(self):
        """Test service creation with missing required fields"""
        # Missing name field
        service_data = {
            'description': 'Professional hair styling service',
            'price': '75.00',
            'duration': 45,
            'hairdresser': self.hairdresser.id
        }
        
        response = self.client.post(
            self.create_url,
            data=json.dumps(service_data),
            content_type='application/json'
        )
        
        # This should return an error due to the missing required field
        self.assertNotEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Missing price field
        service_data = {
            'name': 'Hair Styling',
            'description': 'Professional hair styling service',
            'duration': 45,
            'hairdresser': self.hairdresser.id
        }
        
        response = self.client.post(
            self.create_url,
            data=json.dumps(service_data),
            content_type='application/json'
        )
        
        # This should return an error due to the missing required field
        self.assertNotEqual(response.status_code, status.HTTP_201_CREATED)


class ListServiceTest(ServiceTestCase):
    def test_list_all_services(self):
        """Test listing all services"""
        response = self.client.get(self.list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()['data']), 2)  # 2 services from setup
        
    def test_list_service_by_id(self):
        """Test listing a specific service by ID"""
        response = self.client.get(self.list_service_url(self.service.id))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('data' in response.json())
        service_data = response.json()['data']
        self.assertEqual(service_data['name'], 'Haircut')
        self.assertEqual(service_data['description'], 'Basic haircut service')
        self.assertEqual(Decimal(service_data['price']), Decimal('50.00'))
        self.assertEqual(service_data['duration'], 60)
        
    def test_list_nonexistent_service(self):
        """Test listing a non-existent service"""
        response = self.client.get(self.list_service_url(9999))  # Non-existent ID
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['error'], 'Service not found')

class ListServiceHairdresserTest(TestCase):
    def setUp(self):
        """
        Set up test data for the ListServiceHairdresser view tests
        """
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

        self.empty_hairdresser_user = User.objects.create(
            email="hairdresser@example2.com",
            password="hairdresser123",
            first_name="Test2",
            last_name="Hairdresser2",
            phone="+5592984502224",
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
        
        # Create another hairdresser with no services
        self.empty_hairdresser = Hairdresser.objects.create(
            user=self.empty_hairdresser_user,
            cnpj="12345678901214",
            experience_years=1,
            resume= "ele é um cabeleireiro" 
        )
        
        # Create services for the first hairdresser
        self.service1 = Service.objects.create(
            name="Haircut",
            description="Basic haircut service",
            price=Decimal('50.00'),
            duration=60,
            hairdresser=self.hairdresser
        )
        
        self.service2 = Service.objects.create(
            name="Hair Coloring",
            description="Full hair coloring service",
            price=Decimal('100.00'),
            duration=120,
            hairdresser=self.hairdresser
        )
        
        # URL for listing services of a specific hairdresser
        self.list_services_url = lambda hairdresser_id: reverse('list_service_hairdresser', kwargs={'hairdresser_id': hairdresser_id})
    
    def test_list_services_for_hairdresser(self):
        """
        Test listing services for an existing hairdresser with services
        """
        response = self.client.get(self.list_services_url(self.hairdresser.id))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check the number of services returned
        services_data = response.json()['data']
        self.assertEqual(len(services_data), 2)
        
        # Verify the content of the first service
        first_service = services_data[0]
        self.assertEqual(first_service['name'], 'Haircut')
        self.assertEqual(first_service['description'], 'Basic haircut service')
        self.assertEqual(Decimal(first_service['price']), Decimal('50.00'))
        self.assertEqual(first_service['duration'], 60)
    
    def test_list_services_for_hairdresser_with_no_services(self):
        """
        Test listing services for a hairdresser with no services
        """
        response = self.client.get(self.list_services_url(self.empty_hairdresser.id))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Check that no services are returned
        services_data = response.json()['data']
        self.assertEqual(len(services_data), 0)
    
    def test_list_services_for_nonexistent_hairdresser(self):
        """
        Test listing services for a non-existent hairdresser
        """
        # Use a very high ID that is unlikely to exist
        nonexistent_hairdresser_id = 99999
        
        response = self.client.get(self.list_services_url(nonexistent_hairdresser_id))
        
        # Check for 404 Not Found status
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # Verify the error message
        error_response = response.json()
        self.assertEqual(error_response['error'], 'Hairdresser not found')

class UpdateServiceTest(ServiceTestCase):
    def test_update_service_success(self):
        """Test successful service update"""
        updated_data = {
            'name': 'Premium Haircut',
            'description': 'Updated description',
            'price': '60.00',
            'duration': 75
        }
        
        response = self.client.put(
            self.update_url(self.service.id),
            data=json.dumps(updated_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['message'], 'Service updated successfully')
        
        # Refresh the service from the database
        self.service.refresh_from_db()
        
        # There's a bug in the update method - it assigns tuples instead of values
        # Until fixed, these assertions will fail
        self.assertEqual(self.service.name, 'Premium Haircut')
        self.assertEqual(self.service.description, 'Updated description')
        self.assertEqual(self.service.price, Decimal('60.00'))
        self.assertEqual(self.service.duration, 75)
        
    def test_update_nonexistent_service(self):
        """Test updating a non-existent service"""
        updated_data = {
            'name': 'Premium Haircut',
            'description': 'Updated description',
            'price': '60.00',
            'duration': 75
        }
        
        response = self.client.put(
            self.update_url(9999),  # Non-existent ID
            data=json.dumps(updated_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['error'], 'Service not found')


class RemoveServiceTest(ServiceTestCase):
    def test_remove_service_success(self):
        """Test successful service removal"""
        response = self.client.delete(self.remove_url(self.service.id))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['data'], 'Service register deleted successfully')
        self.assertEqual(Service.objects.count(), 1)  # 2 from setup - 1 deleted
        
    def test_remove_nonexistent_service(self):
        """Test removing a non-existent service"""
        response = self.client.delete(self.remove_url(9999))  # Non-existent ID
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['error'], 'Service not found')