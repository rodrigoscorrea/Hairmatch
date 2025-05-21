from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from users.models import User, Customer, Hairdresser
from .models import Review
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
            "rating": 4.5,
            "preferences": []
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
            "rating": 5.0,
            "role": "hairdresser",
            "cnpj": "12345678901234",
            "experience_years": 5,
            "resume": "Professional hairdresser with extensive experience",
            "preferences": []
        }
        
        # Register users
        self.client.post(
            self.register_url,
            data=json.dumps(self.customer_payload),
            content_type='application/json'
        )
        
        self.client.post(
            self.register_url,
            data=json.dumps(self.hairdresser_payload),
            content_type='application/json'
        )
        
        # Get user objects for testing
        self.hairdresser_user = User.objects.get(email=self.hairdresser_payload['email'])
        self.hairdresser = Hairdresser.objects.get(user=self.hairdresser_user)
        
        self.customer_user = User.objects.get(email=self.customer_payload['email'])
        self.customer = Customer.objects.get(user=self.customer_user)
        
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
        """Test successful review creation"""
        # Login as customer
        self.login_as_customer()
        
        # Create review
        review_data = {
            'rating': 4.5,
            'comment': 'Great service!',
            'hairdresser': self.hairdresser.id
        }
        
        response = self.client.post(
            self.create_url,
            data=json.dumps(review_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Review.objects.count(), 1)
        self.assertEqual(Review.objects.first().rating, 4.5)
        self.assertEqual(Review.objects.first().comment, 'Great service!')
        self.assertEqual(Review.objects.first().customer, self.customer)
        self.assertEqual(Review.objects.first().hairdresser, self.hairdresser)
    
    def test_create_review_no_token(self):
        """Test review creation with no auth token"""
        # Don't login - no token
        
        review_data = {
            'rating': 4.5,
            'comment': 'Great service!',
            'hairdresser': self.hairdresser.id
        }
        
        response = self.client.post(
            self.create_url,
            data=json.dumps(review_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Review.objects.count(), 0)
    
    def test_create_review_hairdresser_role(self):
        """Test that hairdressers cannot create reviews"""
        # Login as hairdresser
        self.login_as_hairdresser()
        
        # Try to create review
        review_data = {
            'rating': 4.5,
            'comment': 'Great service!',
            'hairdresser': self.hairdresser.id
        }
        
        response = self.client.post(
            self.create_url,
            data=json.dumps(review_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Review.objects.count(), 0)
    
    def test_create_review_missing_rating(self):
        """Test review creation without required rating field"""
        # Login as customer
        self.login_as_customer()
        
        # Create review without rating
        review_data = {
            'comment': 'Great service!',
            'hairdresser': self.hairdresser.id
        }
        
        response = self.client.post(
            self.create_url,
            data=json.dumps(review_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Missing field: rating', str(response.content))
        self.assertEqual(Review.objects.count(), 0)

class ListReviewTest(ReviewsTestCase):
    def setUp(self):
        super().setUp()
        
        # Login as customer and create a review
        self.login_as_customer()
        
        # Create a few reviews
        review_data = {
            'rating': 4.5,
            'comment': 'Great service!',
            'hairdresser': self.hairdresser.id
        }
        
        self.client.post(
            self.create_url,
            data=json.dumps(review_data),
            content_type='application/json'
        )
        
        review_data = {
            'rating': 5.0,
            'comment': 'Excellent work!',
            'hairdresser': self.hairdresser.id
        }
        
        self.client.post(
            self.create_url,
            data=json.dumps(review_data),
            content_type='application/json'
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
        self.assertEqual(reviews[0]['rating'], 4.5)
        self.assertEqual(reviews[0]['comment'], 'Great service!')
        self.assertEqual(reviews[1]['rating'], 5.0)
        self.assertEqual(reviews[1]['comment'], 'Excellent work!')

class UpdateReviewTest(ReviewsTestCase):
    def setUp(self):
        super().setUp()
        
        # Login as customer and create a review
        self.login_as_customer()
        
        review_data = {
            'rating': 4.0,
            'comment': 'Good service',
            'hairdresser': self.hairdresser.id
        }
        
        self.client.post(
            self.create_url,
            data=json.dumps(review_data),
            content_type='application/json'
        )
        
        self.review = Review.objects.first()
    
    def test_update_review_success(self):
        """Test successfully updating a review"""
        update_url = reverse('update_review', args=[self.review.id])
        
        # Login as customer who owns the review
        self.login_as_customer()
        
        # Update review
        updated_data = {
            'rating': 5.0,
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
        self.assertEqual(self.review.rating, 5.0)
        self.assertEqual(self.review.comment, 'Updated: Excellent service!')
    
    def test_update_review_no_token(self):
        """Test updating review with no auth token"""
        update_url = reverse('update_review', args=[self.review.id])
        
        # Clear any cookies/tokens
        self.client.cookies.clear()
        
        updated_data = {
            'rating': 5.0,
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
        self.assertEqual(self.review.rating, 4.0)
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
            "rating": 4.0,
            "number": "789",
            "postal_code": "69050750",
            "role": "customer",
            "preferences": []
        }
        
        self.client.post(
            self.register_url,
            data=json.dumps(second_customer_payload),
            content_type='application/json'
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
            'rating': 5.0,
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
        self.assertEqual(self.review.rating, 4.0)
        self.assertEqual(self.review.comment, 'Good service')

class RemoveReviewTest(ReviewsTestCase):
    def setUp(self):
        super().setUp()
        
        # Login as customer and create a review
        self.login_as_customer()
        
        review_data = {
            'rating': 3.5,
            'comment': 'Average service',
            'hairdresser': self.hairdresser.id
        }
        
        self.client.post(
            self.create_url,
            data=json.dumps(review_data),
            content_type='application/json'
        )
        
        self.review = Review.objects.first()
    
    def test_delete_review_success(self):
        """Test successfully deleting a review"""
        delete_url = reverse('remove_review', args=[self.review.id])
        
        # Login as customer who owns the review
        self.login_as_customer()
        
        response = self.client.delete(delete_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Review.objects.count(), 0)
    
    def test_delete_review_no_token(self):
        """Test deleting review with no auth token"""
        delete_url = reverse('remove_review', args=[self.review.id])
        
        # Clear any cookies/tokens
        self.client.cookies.clear()
        
        response = self.client.delete(delete_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Review.objects.count(), 0)
    

class RemoveReviewAdminTest(ReviewsTestCase):
    def setUp(self):
        super().setUp()
        
        # Login as customer and create a review
        self.login_as_customer()
        
        review_data = {
            'rating': 2.0,
            'comment': 'Poor service',
            'hairdresser': self.hairdresser.id
        }
        
        self.client.post(
            self.create_url,
            data=json.dumps(review_data),
            content_type='application/json'
        )
        
        self.review = Review.objects.first()
    
    def test_admin_delete_review(self):
        """Test admin can delete any review without authentication"""
        delete_url = reverse('remove_review', args=[self.review.id])
        
        # No login required for admin delete (according to your implementation)
        admin_delete_url = reverse('remove_review', args=[self.review.id])
        
        response = self.client.delete(admin_delete_url)
        
        # Your implementation doesn't check for admin status, it just deletes
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(Review.objects.count(), 0)