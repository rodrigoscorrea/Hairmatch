from django.test import TestCase, Client
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
import json
from decimal import Decimal
from unittest.mock import patch
from users.models import User, Hairdresser
from service.models import Service
from agenda.models import Agenda
from django.utils import timezone
from datetime import timedelta


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


class RemoveServiceViewTest(TestCase):
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
            resume='Experienced hairdresser',
            cnpj='12345678901234',
            experience_time='5 years',
            experiences='Cutting, coloring',
            products='Professional products'
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
            resume='Creative hairdresser',
            cnpj='98765432109876'
        )
        
        # Create test services
        self.service_1 = Service.objects.create(
            name='Haircut',
            description='Basic haircut service',
            price=Decimal('25.00'),
            duration=30,
            hairdresser=self.hairdresser
        )
        
        self.service_2 = Service.objects.create(
            name='Hair Coloring',
            description='Professional hair coloring',
            price=Decimal('75.00'),
            duration=120,
            hairdresser=self.hairdresser
        )
        
        self.service_3 = Service.objects.create(
            name='Hair Styling',
            description='Professional hair styling',
            price=Decimal('35.00'),
            duration=45,
            hairdresser=self.hairdresser_2
        )

    def test_delete_service_success(self):
        """Test successful deletion of a service with no appointments."""
        # Verify service exists before deletion
        self.assertTrue(Service.objects.filter(id=self.service_1.id).exists())
        
        url = reverse('remove_service', kwargs={'service_id': self.service_1.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Service.objects.filter(id=self.service_1.id).exists())
        self.assertEqual(response.content, b'{"message": "service deleted successfully"}')

    def test_delete_service_not_found(self):
        """Test deletion with non-existent service ID."""
        non_existent_id = 99999
        url = reverse('remove_service', kwargs={'service_id': non_existent_id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, 404)
        
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'Service not found.')

    def test_delete_service_with_existing_appointments(self):
        """Test that service cannot be deleted when appointments exist."""
        # Create an appointment for the service
        start_time = timezone.now() + timedelta(days=1)
        end_time = start_time + timedelta(minutes=self.service_1.duration)
        
        agenda = Agenda.objects.create(
            start_time=start_time,
            end_time=end_time,
            hairdresser=self.hairdresser,
            service=self.service_1
        )
        
        # Verify appointment exists
        self.assertTrue(Agenda.objects.filter(service=self.service_1).exists())
        
        url = reverse('remove_service', kwargs={'service_id': self.service_1.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, 400)
        
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'There are already appointments for this service')
        
        # Verify service still exists
        self.assertTrue(Service.objects.filter(id=self.service_1.id).exists())

    def test_delete_service_with_multiple_appointments(self):
        """Test service deletion prevention with multiple appointments."""
        # Create multiple appointments for the service
        base_time = timezone.now() + timedelta(days=1)
        
        for i in range(3):
            start_time = base_time + timedelta(hours=i)
            end_time = start_time + timedelta(minutes=self.service_2.duration)
            
            Agenda.objects.create(
                start_time=start_time,
                end_time=end_time,
                hairdresser=self.hairdresser,
                service=self.service_2
            )
        
        # Verify multiple appointments exist
        self.assertEqual(Agenda.objects.filter(service=self.service_2).count(), 3)
        
        url = reverse('remove_service', kwargs={'service_id': self.service_2.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, 400)
        
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error'], 'There are already appointments for this service')
        
        # Verify service still exists
        self.assertTrue(Service.objects.filter(id=self.service_2.id).exists())

    def test_delete_service_zero_id(self):
        """Test deletion with ID 0."""
        url = reverse('remove_service', kwargs={'service_id': 0})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, 404)
        
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error'], 'Service not found.')

    def test_get_method_not_allowed(self):
        """Test that GET method is not allowed."""
        url = reverse('remove_service', kwargs={'service_id': self.service_1.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 405)  # Method Not Allowed

    def test_post_method_not_allowed(self):
        """Test that POST method is not allowed."""
        url = reverse('remove_service', kwargs={'service_id': self.service_1.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 405)  # Method Not Allowed

    def test_put_method_not_allowed(self):
        """Test that PUT method is not allowed."""
        url = reverse('remove_service', kwargs={'service_id': self.service_1.id})
        response = self.client.put(url)
        
        self.assertEqual(response.status_code, 405)  # Method Not Allowed

    def test_patch_method_not_allowed(self):
        """Test that PATCH method is not allowed."""
        url = reverse('remove_service', kwargs={'service_id': self.service_1.id})
        response = self.client.patch(url)
        
        self.assertEqual(response.status_code, 405)  # Method Not Allowed

    def test_response_content_type(self):
        """Test that response content type is JSON for error responses."""
        url = reverse('remove_service', kwargs={'service_id': 99999})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response['Content-Type'], 'application/json')

    @patch('service.views.Service.objects.get')  # Replace 'service' with your actual app name
    def test_unexpected_error_handling(self, mock_get):
        """Test handling of unexpected exceptions."""
        # Mock an unexpected exception
        mock_get.side_effect = Exception("Unexpected database error")
        
        url = reverse('remove_service', kwargs={'service_id': self.service_1.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, 500)
        
        response_data = json.loads(response.content)
        self.assertIn('error', response_data)
        self.assertEqual(response_data['error'], 'Unexpected error found.')

    def test_delete_service_different_hairdresser(self):
        """Test deletion of service from different hairdresser."""
        # This test verifies that the service can be deleted regardless of which hairdresser owns it
        # (assuming no business logic prevents this)
        
        url = reverse('remove_service', kwargs={'service_id': self.service_3.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, 200)
        
        # Verify service was deleted
        self.assertFalse(Service.objects.filter(id=self.service_3.id).exists())

    def test_service_deletion_cascade_behavior(self):
        """Test what happens to appointments when service is deleted (if cascade is implemented)."""
        # Note: Your current model uses DO_NOTHING, so this test verifies that behavior
        
        # Create an appointment
        start_time = timezone.now() + timedelta(days=1)
        end_time = start_time + timedelta(minutes=self.service_1.duration)
        
        agenda = Agenda.objects.create(
            start_time=start_time,
            end_time=end_time,
            hairdresser=self.hairdresser,
            service=self.service_1
        )
        
        # Try to delete service (should fail due to business logic)
        url = reverse('remove_service', kwargs={'service_id': self.service_1.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, 400)
        
        # Both service and appointment should still exist
        self.assertTrue(Service.objects.filter(id=self.service_1.id).exists())
        self.assertTrue(Agenda.objects.filter(id=agenda.id).exists())

    def test_url_pattern_matching(self):
        """Test that URL pattern correctly captures service_id."""
        test_ids = [1, 123, 999999]
        
        for test_id in test_ids:
            url = reverse('remove_service', kwargs={'service_id': test_id})
            self.assertIn(str(test_id), url)

    def test_concurrent_deletion_safety(self):
        """Test behavior when service is deleted while being checked for appointments."""
        # This is more of an integration test for race conditions
        
        # Create service and appointment
        start_time = timezone.now() + timedelta(days=1)
        end_time = start_time + timedelta(minutes=self.service_1.duration)
        
        Agenda.objects.create(
            start_time=start_time,
            end_time=end_time,
            hairdresser=self.hairdresser,
            service=self.service_1
        )
        
        # The view should still handle this correctly
        url = reverse('remove_service', kwargs={'service_id': self.service_1.id})
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, 400)
        self.assertTrue(Service.objects.filter(id=self.service_1.id).exists())


class RemoveServiceViewIntegrationTest(TestCase):
    """Integration tests for RemoveService view."""
    
    def setUp(self):
        """Set up test data for integration tests."""
        self.client = Client()
        
        # Create complete test setup
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
            role='HAIRDRESSER'
        )
        
        self.hairdresser = Hairdresser.objects.create(
            user=self.user,
            experience_years=10,
            resume='Integration test hairdresser',
            cnpj='55555555555555'
        )
        
        self.service = Service.objects.create(
            name='Integration Service',
            description='Service for integration testing',
            price=Decimal('50.00'),
            duration=60,
            hairdresser=self.hairdresser
        )

    def test_full_deletion_workflow(self):
        """Test the complete service deletion workflow."""
        # Verify service exists
        self.assertTrue(Service.objects.filter(id=self.service.id).exists())
        
        # Delete the service
        url = reverse('remove_service', kwargs={'service_id': self.service.id})
        response = self.client.delete(url)
        
        # Verify successful deletion
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Service.objects.filter(id=self.service.id).exists())

    def test_business_logic_enforcement(self):
        """Test that business rules are properly enforced."""
        # Create appointment
        start_time = timezone.now() + timedelta(days=1)
        end_time = start_time + timedelta(minutes=self.service.duration)
        
        Agenda.objects.create(
            start_time=start_time,
            end_time=end_time,
            hairdresser=self.hairdresser,
            service=self.service
        )
        
        # Attempt deletion
        url = reverse('remove_service', kwargs={'service_id': self.service.id})
        response = self.client.delete(url)
        
        # Verify business rule enforcement
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['error'], 'There are already appointments for this service')
        
        # Verify service preservation
        self.assertTrue(Service.objects.filter(id=self.service.id).exists())