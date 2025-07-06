from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from users.models import User, Customer, Hairdresser
from .models import Review
from reserve.models import Reserve
from service.models import Service
import jwt
import json

class ReviewsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.create_url = reverse('create_review')
        self.login_url = reverse('login')
        self.register_url = reverse('register')
        
        # Customer user
        self.customer_payload = {
            "email": "customer@example.com",
            "first_name": "Test",
            "last_name": "Customer",
            "password": "password123",
            "phone": "+5592984501111",
            "complement": "Apt 101",
            "neighborhood": "Downtown",
            "city": "Manaus",
            "state": "AM",
            "address": "Customer Street",
            "number": "123",
            "postal_code": "69050750",
            "role": "customer",
            "cpf": "12345678901",
            "rating": 4,
            "preferences": json.dumps([])
        }

        self.customer2_payload = {
            "email": "customer2@example.com",
            "first_name": "Test2",
            "last_name": "Customer",
            "password": "password123",
            "phone": "+5592984501181",
            "complement": "Apt 101",
            "neighborhood": "Downtown",
            "city": "Manaus",
            "state": "AM",
            "address": "Customer Street",
            "number": "123",
            "postal_code": "69050750",
            "role": "customer",
            "cpf": "12345678990",
            "rating": 4,
            "preferences": json.dumps([])
        }
        
        # Hairdresser user
        self.hairdresser_payload = {
            "email": "hairdresser@example.com",
            "first_name": "Test",
            "last_name": "Hairdresser",
            "password": "password123",
            "phone": "+5592984502222",
            "complement": "Apt 202",
            "neighborhood": "Uptown",
            "city": "Manaus",
            "state": "AM",
            "address": "Hairdresser Street",
            "number": "456",
            "postal_code": "69050750",
            "rating": 5,
            "role": "hairdresser",
            "cnpj": "12345678901234",
            "experience_years": 5,
            "resume": "Professional hairdresser with extensive experience",
            "preferences": json.dumps([]),
            'experience_time':'experience_time',
            'experiences':'experiences',
            'products':'products',
            'resume':'resume'
        }
        
        # Register users
        self.client.post(
            self.register_url,
            data=self.customer_payload,
        )

        self.client.post(
            self.register_url,
            data=self.customer2_payload,
        )
        
        self.client.post(
            self.register_url,
            data=self.hairdresser_payload,
        )
        
        # Get user objects for testing
        self.hairdresser_user = User.objects.get(email=self.hairdresser_payload['email'])
        self.hairdresser = Hairdresser.objects.get(user=self.hairdresser_user)
        
        self.customer_user = User.objects.get(email=self.customer_payload['email'])
        self.customer = Customer.objects.get(user=self.customer_user)

        self.customer2_user = User.objects.get(email=self.customer2_payload['email'])
        self.customer2 = Customer.objects.get(user=self.customer2_user)

        self.service = Service.objects.create(
            name="Test Service",
            price=50.00,
            hairdresser=self.hairdresser,
            duration=30
        )
        
        # A reservation is now required to create a review
        self.reserve = Reserve.objects.create(
            customer=self.customer,
            service=self.service
        )

        self.reserve2 = Reserve.objects.create(
            customer=self.customer,
            service=self.service
        )
        
    def login_as_customer(self):
        """Helper method to login as customer and get token"""
        login_payload = {
            'email': self.customer_payload['email'],
            'password': self.customer_payload['password']
        }
        
        response = self.client.post(
            self.login_url,
            data=json.dumps(login_payload),
            content_type='application/json'
        )
        return response
    
    def login_as_hairdresser(self):
        """Helper method to login as hairdresser and get token"""
        login_payload = {
            'email': self.hairdresser_payload['email'],
            'password': self.hairdresser_payload['password']
        }
        
        response = self.client.post(
            self.login_url,
            data=json.dumps(login_payload),
            content_type='application/json'
        )
        return response 

class CreateReviewTest(ReviewsTestCase):
    def test_create_review_success(self):
        """Test successful review creation linked to a reservation."""
        self.login_as_customer()
        
        review_data = {
            'rating': 5,
            'comment': 'Amazing service!',
            'hairdresser': self.hairdresser.id,
            'reserve': self.reserve.id  # <-- Required field
        }
        
        response = self.client.post(self.create_url, data=review_data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Review.objects.count(), 1)
        
        # Verify the review content
        created_review = Review.objects.first()
        self.assertEqual(created_review.rating, 5)
        self.assertEqual(created_review.comment, 'Amazing service!')
        self.assertEqual(created_review.customer, self.customer)
        
        # Verify the reservation is updated
        self.reserve.refresh_from_db()
        self.assertEqual(self.reserve.review, created_review)

    def test_create_review_missing_reserve_id(self):
        """Test that providing no reserve ID results in a 400 Bad Request."""
        self.login_as_customer()
        
        review_data = { # Missing 'reserve' key
            'rating': 4,
            'comment': 'No reserve id!',
            'hairdresser': self.hairdresser.id
        }
        
        response = self.client.post(self.create_url, data=review_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Missing field: reserve', str(response.content))
        
    def test_create_review_reserve_not_found(self):
        """Test that using a non-existent reserve ID results in a 404 Not Found."""
        self.login_as_customer()

        review_data = {
            'rating': 4,
            'comment': 'Bad reserve id!',
            'hairdresser': self.hairdresser.id,
            'reserve': 9999 # Non-existent ID
        }

        response = self.client.post(self.create_url, data=review_data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_review_not_authorized_for_reserve(self):
        """Test that a user cannot review a reservation that isn't theirs."""
        # Create a second customer and log them in
        #other_user = self.customer2_user
        #Customer.objects.create(user=other_user, cpf="11122233344")
        self.client.login(email=self.customer2_user.email, password=self.customer2_user.password)

        # Try to review the first customer's reservation
        review_data = {
            'rating': 1,
            'comment': 'Trying to review someone elses booking',
            'hairdresser': self.hairdresser.id,
            'reserve': self.reserve.id
        }
        
        response = self.client.post(self.create_url, data=review_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_review_no_token(self):
        """Test review creation fails when not authenticated (403 Forbidden)."""
        # Note: self.client is not logged in
        review_data = {
            'rating': 4,
            'comment': 'No token!',
            'hairdresser': self.hairdresser.id,
            'reserve': self.reserve.id
        }
        response = self.client.post(self.create_url, data=review_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
class ListReviewTest(ReviewsTestCase):
    def setUp(self):
        super().setUp()
        
        # Login as customer and create a review
        self.login_as_customer()
        
        # Create a few reviews
        review_data = {
            'rating': 4,
            'comment': 'Great service!',
            'hairdresser': self.hairdresser.id,
            'reserve': self.reserve.id
        }
        
        self.client.post(
            self.create_url,
            data=review_data,
        )
        
        review_data = {
            'rating': 5,
            'comment': 'Excellent work!',
            'hairdresser': self.hairdresser.id,
            'reserve': self.reserve2.id
        }
        
        self.client.post(
            self.create_url,
            data=review_data,
        )
    
    def test_list_reviews(self):
        """Test listing reviews for a hairdresser"""
        list_url = reverse('list_review', args=[self.hairdresser.id])
        
        # No login required for listing
        response = self.client.get(list_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = json.loads(response.content)
        self.assertEqual(len(response_data['data']), 2)
        
        # Verify review data
        reviews = response_data['data']
        self.assertEqual(reviews[0]['rating'], 4)
        self.assertEqual(reviews[0]['comment'], 'Great service!')
        self.assertEqual(reviews[1]['rating'], 5)
        self.assertEqual(reviews[1]['comment'], 'Excellent work!')

class UpdateReviewTest(ReviewsTestCase):
    def setUp(self):
        super().setUp()
        
        # Login as customer and create a review
        self.login_as_customer()
        
        review_data = {
            'rating': 4,
            'comment': 'Good service',
            'hairdresser': self.hairdresser.id,
            'reserve': self.reserve.id
        }
        
        self.client.post(
            self.create_url,
            data=review_data,
        )
        
        self.review = Review.objects.first()
    
    def test_update_review_success(self):
        """Test successfully updating a review"""
        update_url = reverse('update_review', args=[self.review.id])
        
        # Login as customer who owns the review
        self.login_as_customer()
        
        # Update review
        updated_data = {
            'rating': 5,
            'comment': 'Updated: Excellent service!'
        }
        
        response = self.client.put(
            update_url,
            data=json.dumps(updated_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify updated data
        self.review.refresh_from_db()
        self.assertEqual(self.review.rating, 5)
        self.assertEqual(self.review.comment, 'Updated: Excellent service!')
    
    def test_update_review_no_token(self):
        """Test updating review with no auth token"""
        update_url = reverse('update_review', args=[self.review.id])
        
        # Clear any cookies/tokens
        self.client.cookies.clear()
        
        updated_data = {
            'rating': 5,
            'comment': 'Updated comment'
        }
        
        response = self.client.put(
            update_url,
            data=json.dumps(updated_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        
        # Verify data was not updated
        self.review.refresh_from_db()
        self.assertEqual(self.review.rating, 4)
        self.assertEqual(self.review.comment, 'Good service')
    
    def test_update_review_wrong_user(self):
        """Test updating review by a different user"""
        # Create a second customer
        second_customer_payload = {
            "email": "customer2@example.com",
            "first_name": "Second",
            "last_name": "Customer",
            "password": "password123",
            "phone": "+5592984503333",
            "complement": "Apt 303",
            "neighborhood": "Midtown",
            "city": "Manaus",
            "state": "AM",
            "address": "Second Street",
            "cpf": "12345678901",
            "rating": 4,
            "number": "789",
            "postal_code": "69050750",
            "role": "customer",
            "preferences": json.dumps([])
        }
        
        self.client.post(
            self.register_url,
            data=second_customer_payload,
        )
        
        # Login as second customer
        login_payload = {
            'email': second_customer_payload['email'],
            'password': second_customer_payload['password']
        }
        
        self.client.post(
            self.login_url,
            data=json.dumps(login_payload),
            content_type='application/json'
        )
        
        # Try to update the review
        update_url = reverse('update_review', args=[self.review.id])
        
        updated_data = {
            'rating': 5,
            'comment': 'Updated comment'
        }
        
        response = self.client.put(
            update_url,
            data=json.dumps(updated_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND) # Review not found for this user
        
        # Verify data was not changed
        self.review.refresh_from_db()
        self.assertEqual(self.review.rating, 4)
        self.assertEqual(self.review.comment, 'Good service')

class RemoveReview(ReviewsTestCase):
    def setUp(self):
        """
        Set up a review that is linked to the reservation for testing deletion.
        """
        super().setUp()
        
        # Create a review as the customer
        self.login_as_customer()
        review_raw = Review.objects.create(
            rating=3,
            customer=Customer.objects.get(id=self.customer.id),
            comment= 'An average service',
            hairdresser=Hairdresser.objects.get(id=self.hairdresser.id),
            reserve=Reserve.objects.get(id=self.reserve.id),
        )
        review_raw.save()
    
        # Get the created review and link it to the reserve to test unlinking
        self.review = Review.objects.first()
        self.reserve.review = self.review
        self.reserve.save()
        self.delete_url = reverse('remove_review', args=[self.review.id])

    def test_delete_review_success(self):
        """Test a customer can successfully delete their own review."""
        # Ensure the customer is logged in
        #self.client.login(email=self.customer_user.email, password="senha123")
        self.login_as_customer()
        response = self.client.delete(self.delete_url)
        
        # A successful deletion with no content should return 204 - but it will return 200 due to axios problems in the frontend
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Review.objects.count(), 0)
        
        # Assert that the review was unlinked from the reserve
        self.reserve.refresh_from_db()
        self.assertIsNone(self.reserve.review)

    def test_delete_review_unauthenticated(self):
        """Test that an unauthenticated request is forbidden."""
        # Log out the client
        self.client.logout()
        
        response = self.client.delete(self.delete_url)
        
        # The view should return 403 FORBIDDEN, not 200
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Review.objects.count(), 1) # The review should NOT be deleted

    def test_delete_non_existent_review(self):
        """Test that trying to delete a review that doesn't exist returns 404."""
        self.client.login(email=self.customer_user.email, password="senha123")
        
        # Use an ID that does not exist
        invalid_delete_url = reverse('remove_review', args=[9999])
        response = self.client.delete(invalid_delete_url)
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

class RemoveAdminDeleteReview(ReviewsTestCase):
    def setUp(self):
        super().setUp()
        self.review = Review.objects.create(
            rating=1,
            comment="A review to be deleted",
            customer=self.customer,
            hairdresser=self.hairdresser
        )
        self.admin_delete_url = reverse('remove_review_admin', args=[self.review.id])

    def test_admin_can_delete_review(self):
        """Test that the admin endpoint successfully deletes a review."""
        response = self.client.delete(self.admin_delete_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Review.objects.count(), 0)

    def test_admin_delete_non_existent_review(self):
        """Test that the admin endpoint returns 404 for a review that doesn't exist."""
        invalid_url = reverse('remove_review_admin', args=[9999])
        response = self.client.delete(invalid_url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)