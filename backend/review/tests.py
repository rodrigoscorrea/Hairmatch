from hairmatch.problem_testing import assert_problem
from io import BytesIO
from django.core.files.storage import default_storage
import threading
from django.db import connection
from django.test import SimpleTestCase, TestCase, TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse, NoReverseMatch
from rest_framework.test import APIClient
from rest_framework import status
from django.core.files.uploadedfile import SimpleUploadedFile
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from PIL import Image
from hairmatch.image_fixtures import make_upload
from users.models import User, Customer, Hairdresser
from users.testing import activate_account
from django.db import IntegrityError, transaction
from hairmatch.problems import Problem
from .customer_ratings import record_customer_rating, service_end
from .models import CustomerRating, Review, ReviewPicture
from .pictures import (
    MAX_REVIEW_PICTURES, REVIEW_PICTURE_MAX_SIZE, add_review_pictures, picture_errors, picture_names,
)
from hairmatch.images import InvalidImage
from reserve.models import Reserve
from service.models import Service
import jwt
import json
import re
import datetime
from django.conf import settings
from django.utils import timezone
from users.cognito import get_cognito

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
            "password": "Password123",
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
            "password": "Password123",
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
            "password": "Password123",
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
        activate_account(self.customer_payload['email'])

        self.client.post(
            self.register_url,
            data=self.customer2_payload,
        )
        activate_account(self.customer2_payload['email'])
        
        self.client.post(
            self.register_url,
            data=self.hairdresser_payload,
        )
        activate_account(self.hairdresser_payload['email'])
        
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

    def test_create_review_with_picture_stores_a_webp(self):
        """WEBP-03: the picture is saved as reviews/images/<stem>.webp with WebP content."""
        self.login_as_customer()

        response = self.client.post(self.create_url, data={
            'rating': 5,
            'comment': 'With photo',
            'hairdresser': self.hairdresser.id,
            'reserve': self.reserve.id,
            'picture': make_upload('review_photo.png', fmt='PNG'),
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        review = Review.objects.get()
        self.assertEqual(review.picture.name, 'reviews/images/review_photo.webp')
        with default_storage.open(review.picture.name) as stored:
            self.assertEqual(Image.open(BytesIO(stored.read())).format, 'WEBP')

    def _post_review_with_picture(self, picture):
        return self.client.post(self.create_url, data={
            'rating': 5,
            'comment': 'With photo',
            'hairdresser': self.hairdresser.id,
            'reserve': self.reserve.id,
            'picture': picture,
        })

    def _assert_rejected_with_no_review(self, response):
        assert_problem(response, 'invalid-image', detail='The review picture is not a valid image.')
        self.assertEqual(Review.objects.count(), 0)
        self.reserve.refresh_from_db()
        self.assertIsNone(self.reserve.review)

    def test_create_review_with_a_file_that_is_not_an_image_returns_400(self):
        """WEBP-12: nothing is created and the reservation stays unreviewed."""
        self.login_as_customer()

        response = self._post_review_with_picture(
            SimpleUploadedFile('notes.jpg', b'just some notes', content_type='image/jpeg')
        )

        self._assert_rejected_with_no_review(response)

    def test_create_review_with_an_image_over_the_pixel_limit_returns_400(self):
        """WEBP-13: a decompression bomb gets the same answer as an invalid image."""
        self.login_as_customer()

        with patch.object(Image, 'MAX_IMAGE_PIXELS', 10):
            response = self._post_review_with_picture(make_upload('big.jpg'))

        self._assert_rejected_with_no_review(response)

    def test_create_review_missing_reserve_id(self):
        """Test that providing no reserve ID results in a 400 Bad Request."""
        self.login_as_customer()
        
        review_data = { # Missing 'reserve' key
            'rating': 4,
            'comment': 'No reserve id!',
            'hairdresser': self.hairdresser.id
        }
        
        response = self.client.post(self.create_url, data=review_data)
        assert_problem(response, 'validation-error', errors=[
            {'pointer': '#/reserve', 'detail': 'This field is required.'},
        ])
        
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
        assert_problem(response, 'not-found', detail='Reservation not found.')

    def test_create_review_not_authorized_for_reserve(self):
        """Test that a user cannot review a reservation that isn't theirs."""
        # Create a second customer and log them in
        #other_user = self.customer2_user
        #Customer.objects.create(user=other_user, cpf="11122233344")
        # (Django's client.login sets no jwt cookie, so this used to run unauthenticated and only
        # passed on the old 403 for a missing cookie. Log in through the API to reach the permission check.)
        self.client.post(
            self.login_url,
            data=json.dumps({
                'email': self.customer2_payload['email'],
                'password': self.customer2_payload['password'],
            }),
            content_type='application/json',
        )

        # Try to review the first customer's reservation
        review_data = {
            'rating': 1,
            'comment': 'Trying to review someone elses booking',
            'hairdresser': self.hairdresser.id,
            'reserve': self.reserve.id
        }
        
        response = self.client.post(self.create_url, data=review_data)
        assert_problem(response, 'forbidden')

    def test_create_review_no_token(self):
        """Test review creation fails when not authenticated (401 Unauthorized)."""
        # Note: self.client is not logged in
        review_data = {
            'rating': 4,
            'comment': 'No token!',
            'hairdresser': self.hairdresser.id,
            'reserve': self.reserve.id
        }
        response = self.client.post(self.create_url, data=review_data)
        assert_problem(response, 'invalid-session')
class CreateReviewProblemsTest(ReviewsTestCase):
    """Every way the create endpoint refuses a review answers with a problem that names the field."""

    def _post(self, **overrides):
        data = {'reserve': self.reserve.id, 'rating': 4, 'comment': 'ok', 'hairdresser': self.hairdresser.id}
        data.update(overrides)
        return self.client.post(self.create_url, data=data)

    def setUp(self):
        super().setUp()
        self.login_as_customer()

    def test_no_fields_reports_reserve_rating_and_hairdresser(self):
        response = self.client.post(self.create_url, data={})

        assert_problem(response, 'validation-error', errors=[
            {'pointer': '#/reserve', 'detail': 'This field is required.'},
            {'pointer': '#/rating', 'detail': 'This field is required.'},
            {'pointer': '#/hairdresser', 'detail': 'This field is required.'},
        ])

    def test_a_rating_that_is_not_a_finite_number_is_refused(self):
        for rating in ('great', 'nan', 'inf'):
            with self.subTest(rating=rating):
                assert_problem(self._post(rating=rating), 'validation-error', errors=[
                    {'pointer': '#/rating', 'detail': 'This field must be a number.'},
                ])
        self.assertEqual(Review.objects.filter(comment='ok').count(), 0)

    def test_a_rating_outside_1_to_5_is_refused(self):
        for rating in ('0', '0.9', '5.1', '6', '-1e300'):
            with self.subTest(rating=rating):
                assert_problem(self._post(rating=rating), 'validation-error', errors=[
                    {'pointer': '#/rating', 'detail': 'The rating must be between 1 and 5.'},
                ])
        self.assertEqual(Review.objects.filter(comment='ok').count(), 0)

    def test_the_lowest_rating_is_accepted(self):
        response = self._post(rating='1')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Review.objects.get(comment='ok').rating, 1)

    def test_ids_that_are_not_integers_are_refused(self):
        assert_problem(self._post(reserve='abc', hairdresser='x'), 'validation-error', errors=[
            {'pointer': '#/reserve', 'detail': 'This field must be an integer.'},
            {'pointer': '#/hairdresser', 'detail': 'This field must be an integer.'},
        ])

    def test_a_reserve_that_was_already_reviewed_answers_409(self):
        self.reserve.review = Review.objects.create(
            rating=3, comment='first', customer=self.customer, hairdresser=self.hairdresser
        )
        self.reserve.save()

        response = self._post()

        assert_problem(response, 'review-exists', detail='This reservation has already been reviewed.')
        self.assertEqual(Review.objects.filter(customer=self.customer).count(), 1)

    def test_a_hairdresser_that_does_not_exist_answers_404(self):
        assert_problem(self._post(hairdresser=999999), 'not-found', detail='Hairdresser not found.')
        self.assertFalse(Review.objects.filter(comment='ok').exists())

    def test_a_hairdresser_account_creating_a_review_answers_403_customer_required(self):
        self.login_as_hairdresser()

        response = self._post()

        assert_problem(response, 'customer-required', detail='Only customers can perform this action.')

    def test_an_unexpected_failure_is_a_500_without_the_exception_text(self):
        with patch.object(Review.objects, 'create', side_effect=RuntimeError('disk full')):
            with self.assertLogs('hairmatch.problems', level='ERROR'):
                response = self._post()

        body = assert_problem(response, 'internal-error', detail='An unexpected error occurred.')
        self.assertNotIn('disk full', json.dumps(body))
        self.reserve.refresh_from_db()
        self.assertIsNone(self.reserve.review)


class UpdateReviewProblemsTest(ReviewsTestCase):
    def setUp(self):
        super().setUp()
        self.login_as_customer()
        self.review = Review.objects.create(
            rating=4, comment='Good service', customer=self.customer, hairdresser=self.hairdresser
        )
        self.url = reverse('review_detail', args=[self.review.id])

    def _put(self, body):
        if not isinstance(body, str):
            body = json.dumps(body)
        return self.client.put(self.url, data=body, content_type='application/json')

    def test_a_body_that_is_not_json_answers_400(self):
        for raw in ('{nope', '[1]'):
            with self.subTest(raw=raw):
                assert_problem(self._put(raw), 'malformed-request')

    def test_a_missing_rating_answers_400(self):
        assert_problem(self._put({'comment': 'only'}), 'validation-error', errors=[
            {'pointer': '#/rating', 'detail': 'This field is required.'},
        ])

    def test_a_rating_that_is_not_a_number_answers_400(self):
        assert_problem(self._put({'rating': 'top'}), 'validation-error', errors=[
            {'pointer': '#/rating', 'detail': 'This field must be a number.'},
        ])
        self.review.refresh_from_db()
        self.assertEqual(self.review.rating, 4)

    def test_a_rating_outside_1_to_5_answers_400_and_keeps_the_review(self):
        for rating in (0, 6, -1e300):
            with self.subTest(rating=rating):
                assert_problem(self._put({'rating': rating}), 'validation-error', errors=[
                    {'pointer': '#/rating', 'detail': 'The rating must be between 1 and 5.'},
                ])
        self.review.refresh_from_db()
        self.assertEqual(self.review.rating, 4)

    def test_the_bounds_of_the_rating_are_accepted(self):
        for rating in (1, 5):
            with self.subTest(rating=rating):
                self.assertEqual(self._put({'rating': rating}).status_code, status.HTTP_200_OK)
                self.review.refresh_from_db()
                self.assertEqual(self.review.rating, rating)

    def test_a_picture_in_the_body_is_ignored(self):
        response = self._put({'rating': 5, 'picture': '../../outro-usuario/profile_pictures/x.webp'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.review.refresh_from_db()
        self.assertFalse(self.review.picture)
        self.assertEqual(self.review.rating, 5)


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
        update_url = reverse('review_detail', args=[self.review.id])
        
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
        update_url = reverse('review_detail', args=[self.review.id])
        
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
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        assert_problem(response, 'invalid-session')
        
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
            "password": "Password123",
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
        update_url = reverse('review_detail', args=[self.review.id])
        
        updated_data = {
            'rating': 5,
            'comment': 'Updated comment'
        }
        
        response = self.client.put(
            update_url,
            data=json.dumps(updated_data),
            content_type='application/json'
        )
        
        assert_problem(response, 'not-found', detail='Review not found.')  # Review not found for this user
        
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
        )

        # Link the review to the reserve (Reserve owns the relation) to test unlinking
        self.review = review_raw
        self.reserve.review = self.review
        self.reserve.save()
        self.delete_url = reverse('review_detail', args=[self.review.id])

    def test_delete_review_success(self):
        """Test a customer can successfully delete their own review."""
        # Ensure the customer is logged in
        #self.client.login(email=self.customer_user.email, password="senha123")
        self.login_as_customer()
        response = self.client.delete(self.delete_url)
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.content, b'')
        self.assertEqual(Review.objects.count(), 0)
        
        # Assert that the review was unlinked from the reserve
        self.reserve.refresh_from_db()
        self.assertIsNone(self.reserve.review)

    def test_delete_review_unauthenticated(self):
        """Test that an unauthenticated request is forbidden."""
        # Log out the client
        self.client.logout()
        
        response = self.client.delete(self.delete_url)
        
        # The view should return 401 UNAUTHORIZED, not 200
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        assert_problem(response, 'invalid-session')
        self.assertEqual(Review.objects.count(), 1) # The review should NOT be deleted

    def test_delete_non_existent_review(self):
        """Test that trying to delete a review that doesn't exist returns 404."""
        # Use an ID that does not exist
        invalid_delete_url = reverse('review_detail', args=[9999])
        response = self.client.delete(invalid_delete_url)
        
        assert_problem(response, 'not-found', detail='Review not found.')

class RemovedAdminDeleteRouteTest(ReviewsTestCase):
    """removeAdm had no auth nor role check and was removed (#151)."""

    def test_remove_admin_route_no_longer_exists(self):
        review = Review.objects.create(
            rating=1, comment="A review", customer=self.customer, hairdresser=self.hairdresser
        )

        with self.assertRaises(NoReverseMatch):
            reverse('remove_review_admin', args=[review.id])
        response = self.client.delete(f'/api/review/removeAdm/{review.id}')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Review.objects.filter(id=review.id).exists())

class ReviewSessionTest(ReviewsTestCase):
    """The three cookie-based review routes authenticate through the central authenticator."""

    def setUp(self):
        super().setUp()
        self.customer_user.cognito_sub = 'sub-customer'
        self.customer_user.save()
        self.fake = get_cognito().client

    def _cognito_token(self):
        return self.fake.make_access_token('sub-customer')

    def _google_token(self):
        now = int(datetime.datetime.now().timestamp())
        return jwt.encode(
            {'id': self.customer_user.id, 'iss': 'hairmatch', 'token_use': 'session',
             'iat': now, 'exp': now + 3600},
            settings.SECRET_KEY, algorithm='HS256',
        )

    def _call(self, route, token):
        self.client.cookies.clear()
        if token:
            self.client.cookies['jwt'] = token
        if route == 'create':
            reserve = Reserve.objects.create(customer=self.customer, service=self.service)
            return self.client.post(self.create_url, data={
                'rating': 4, 'comment': 'ok', 'hairdresser': self.hairdresser.id, 'reserve': reserve.id,
            })
        review = Review.objects.create(
            rating=4, comment='Good', customer=self.customer, hairdresser=self.hairdresser
        )
        Reserve.objects.create(customer=self.customer, service=self.service, review=review)
        if route == 'update':
            return self.client.put(
                reverse('review_detail', args=[review.id]),
                data=json.dumps({'rating': 5}), content_type='application/json',
            )
        return self.client.delete(reverse('review_detail', args=[review.id]))

    def test_routes_accept_a_cognito_access_token_and_a_google_session(self):
        expected = {'create': 201, 'update': 200, 'delete': 204}
        for token_kind in ('cognito', 'google'):
            for route, status_code in expected.items():
                with self.subTest(token=token_kind, route=route):
                    token = self._cognito_token() if token_kind == 'cognito' else self._google_token()
                    self.assertEqual(self._call(route, token).status_code, status_code)

    def test_routes_refuse_a_missing_cookie_and_a_cognito_refresh_token_with_401(self):
        refresh_token = self.fake.make_refresh_token('sub-customer')
        for route in ('create', 'update', 'delete'):
            for token in (None, refresh_token):
                with self.subTest(route=route, refresh=token is not None):
                    before = Review.objects.count()
                    response = self._call(route, token)
                    self.assertEqual(response.status_code, 401)
                    assert_problem(response, 'invalid-session')
                    # _call itself adds one review for update/delete, and the route must not change it
                    self.assertEqual(Review.objects.count(), before + (0 if route == 'create' else 1))


class ReviewOwnershipTest(ReviewsTestCase):
    """Review writes stay limited to the customer of the reservation."""

    def setUp(self):
        super().setUp()
        self.other_hairdresser_payload = dict(
            self.hairdresser_payload, email='other.hairdresser@example.com', phone='+5592984509999',
        )
        self.client.post(self.register_url, data=self.other_hairdresser_payload)
        activate_account(self.other_hairdresser_payload['email'])
        self.other_hairdresser = Hairdresser.objects.get(user__email='other.hairdresser@example.com')
        self.review = Review.objects.create(
            rating=4, comment='Good', customer=self.customer, hairdresser=self.hairdresser
        )
        self.reserve2.review = self.review
        self.reserve2.save()

    def test_create_review_for_a_hairdresser_other_than_the_reserved_one_is_refused(self):
        self.login_as_customer()

        response = self.client.post(self.create_url, data={
            'rating': 1, 'comment': 'fake', 'hairdresser': self.other_hairdresser.id, 'reserve': self.reserve.id,
        })

        assert_problem(response, 'validation-error', errors=[
            {'pointer': '#/hairdresser', 'detail': 'The hairdresser does not match the reservation.'},
        ])
        self.assertFalse(Review.objects.filter(hairdresser=self.other_hairdresser).exists())
        self.reserve.refresh_from_db()
        self.assertIsNone(self.reserve.review)

    def test_hairdresser_cannot_update_or_remove_a_review_with_403(self):
        self.login_as_hairdresser()

        update = self.client.put(
            reverse('review_detail', args=[self.review.id]),
            data=json.dumps({'rating': 1}), content_type='application/json',
        )
        remove = self.client.delete(reverse('review_detail', args=[self.review.id]))

        assert_problem(update, 'customer-required', detail='Only customers can perform this action.')
        assert_problem(remove, 'customer-required', detail='Only customers can perform this action.')
        self.review.refresh_from_db()
        self.assertEqual(self.review.rating, 4)


class CustomerRatingModelTest(ReviewsTestCase):
    """The table keeps one rating from 1 to 5 per reservation, and outlives the reservation and its author."""

    def setUp(self):
        super().setUp()
        # A stored average, to show that deleting rows around a rating does not touch it.
        self.customer_user.rating = 4.0
        self.customer_user.save(update_fields=['rating'])
        self.rating = CustomerRating.objects.create(
            reservation=self.reserve, customer=self.customer, hairdresser=self.hairdresser, rating=4, comment='Pontual',
        )

    def _create(self, **fields):
        values = {'customer': self.customer, 'hairdresser': self.hairdresser, 'rating': 3, **fields}
        with transaction.atomic():
            return CustomerRating.objects.create(**values)

    def test_a_rating_outside_1_to_5_is_refused_by_the_database(self):
        for value in (0, 6):
            with self.subTest(rating=value):
                with self.assertRaises(IntegrityError):
                    self._create(reservation=self.reserve2, rating=value)
        self.assertEqual(CustomerRating.objects.count(), 1)

    def test_a_second_rating_of_the_same_reservation_is_refused_by_the_database(self):
        """CRT-06"""
        with self.assertRaises(IntegrityError):
            self._create(reservation=self.reserve)
        self.assertEqual(CustomerRating.objects.filter(reservation=self.reserve).count(), 1)

    def test_ratings_without_a_reservation_coexist(self):
        """CRT-24: the unique reservation does not stop many ratings whose reservation is gone."""
        self._create(reservation=None)
        self._create(reservation=None)

        self.assertEqual(CustomerRating.objects.filter(reservation__isnull=True).count(), 2)

    def test_cancelling_a_rated_reservation_keeps_the_rating_and_the_average(self):
        """CRT-24"""
        self.login_as_customer()

        response = self.client.delete(reverse('reservation_detail', args=[self.reserve.id]))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Reserve.objects.filter(id=self.reserve.id).exists())
        self.rating.refresh_from_db()
        self.assertIsNone(self.rating.reservation)
        self.assertEqual((self.rating.rating, self.rating.customer_id), (4, self.customer.id))
        self.customer_user.refresh_from_db()
        self.assertEqual(self.customer_user.rating, 4.0)

    def test_deleting_the_author_account_keeps_the_rating_and_the_average(self):
        """CRT-25"""
        self.login_as_hairdresser()

        response = self.client.delete(reverse('current_user'))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Hairdresser.objects.filter(id=self.hairdresser.id).exists())
        self.rating.refresh_from_db()
        self.assertIsNone(self.rating.hairdresser)
        self.assertEqual((self.rating.rating, self.rating.customer_id), (4, self.customer.id))
        self.customer_user.refresh_from_db()
        self.assertEqual(self.customer_user.rating, 4.0)

    def test_deleting_the_customer_account_deletes_the_ratings_received(self):
        """CRT-26"""
        self._create(reservation=None)
        other = CustomerRating.objects.create(customer=self.customer2, hairdresser=self.hairdresser, rating=5)
        self.login_as_customer()

        response = self.client.delete(reverse('current_user'))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(CustomerRating.objects.filter(customer_id=self.customer.id).exists())
        self.assertTrue(CustomerRating.objects.filter(id=other.id).exists())


class RecordCustomerRatingTest(ReviewsTestCase):
    """record_customer_rating: the rating and the customer's new average are written together."""

    def _reserve(self, customer=None):
        return Reserve.objects.create(customer=customer or self.customer, service=self.service)

    def _record(self, reservation, rating, comment=None):
        return record_customer_rating(self.hairdresser, reservation, rating, comment)

    def test_the_average_is_stored_with_2_decimals(self):
        """CRT-18: 5, 4 and 4 average 4.33."""
        for value in (5, 4, 4):
            self._record(self._reserve(), value)

        self.customer_user.refresh_from_db()
        self.assertEqual(self.customer_user.rating, 4.33)

    def test_a_single_rating_is_the_average(self):
        """CRT-01 and CRT-18"""
        created = self._record(self.reserve, 3, 'Pontual')

        self.customer_user.refresh_from_db()
        self.assertEqual(self.customer_user.rating, 3.0)
        created.refresh_from_db()
        self.assertEqual(
            (created.reservation_id, created.customer_id, created.hairdresser_id, created.rating, created.comment),
            (self.reserve.id, self.customer.id, self.hairdresser.id, 3, 'Pontual'),
        )

    def test_a_customer_without_ratings_keeps_none(self):
        """CRT-20"""
        self._record(self.reserve, 5)

        self.customer2_user.refresh_from_db()
        self.assertIsNone(self.customer2_user.rating)

    def test_rating_a_rated_reservation_raises_review_exists_and_changes_nothing(self):
        """CRT-06: the unique reservation turns into review-exists, and the caller's transaction stays usable."""
        self._record(self.reserve, 5)

        with transaction.atomic():
            with self.assertRaises(Problem) as raised:
                self._record(self.reserve, 1)
            # A query in the same transaction would raise TransactionManagementError if it were broken.
            self.assertEqual(CustomerRating.objects.count(), 1)

        self.assertEqual(raised.exception.slug, 'review-exists')
        self.assertEqual(CustomerRating.objects.get().rating, 5)
        self.customer_user.refresh_from_db()
        self.assertEqual(self.customer_user.rating, 5.0)

    def test_the_customer_row_is_locked_before_the_insert(self):
        """CRT-19"""
        with CaptureQueriesContext(connection) as queries:
            self._record(self.reserve, 4)

        statements = [query['sql'] for query in queries.captured_queries]
        lock = next(
            i for i, sql in enumerate(statements) if 'FOR UPDATE' in sql and 'FROM "users_user"' in sql
        )
        insert = next(i for i, sql in enumerate(statements) if sql.startswith('INSERT INTO "review_customerrating"'))
        self.assertLess(lock, insert)

    def test_service_end_is_the_start_plus_the_duration(self):
        """CRT-02: the service lasts 30 minutes."""
        start = datetime.datetime(2026, 10, 9, 13, 0, tzinfo=datetime.timezone.utc)
        reservation = Reserve.objects.create(customer=self.customer, service=self.service, start_time=start)

        self.assertEqual(service_end(reservation), datetime.datetime(2026, 10, 9, 13, 30, tzinfo=datetime.timezone.utc))

    def test_service_end_is_none_without_a_start_time(self):
        """CRT-04"""
        reservation = Reserve.objects.create(customer=self.customer, service=self.service, start_time=None)

        self.assertIsNone(service_end(reservation))


class CustomerRatingRaceTest(TransactionTestCase):
    """CRT-19: two hairdressers rate the same customer at the same time, and the average counts both."""

    def _user(self, email, phone, role):
        return User.objects.create(
            first_name='Race', last_name=role, email=email, phone=phone, neighborhood='Centro', city='Manaus',
            state='AM', address='Rua A', postal_code='69000000', role=role,
        )

    def test_concurrent_ratings_of_the_same_customer_both_count(self):
        customer = Customer.objects.create(user=self._user('c@example.com', '5592900000010', 'customer'), cpf='1')
        work = []
        for index, value in ((1, 5), (2, 1)):
            hairdresser = Hairdresser.objects.create(
                user=self._user(f'h{index}@example.com', f'559290000002{index}', 'hairdresser'), cnpj='1',
            )
            service = Service.objects.create(name='Corte', price=50, hairdresser=hairdresser, duration=30)
            work.append((hairdresser, Reserve.objects.create(customer=customer, service=service), value))
        barrier = threading.Barrier(len(work))
        failures = []

        def rate(hairdresser, reservation, value):
            try:
                barrier.wait(timeout=10)
                record_customer_rating(hairdresser, reservation, value, None)
            except Exception as exc:  # reported below: an exception in a thread does not fail the test
                failures.append(exc)
            finally:
                connection.close()

        threads = [threading.Thread(target=rate, args=args) for args in work]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        self.assertEqual(failures, [])
        self.assertEqual(CustomerRating.objects.filter(customer=customer).count(), 2)
        self.assertEqual(User.objects.get(pk=customer.user_id).rating, 3.0)


class CreateCustomerRatingTest(ReviewsTestCase):
    """POST /api/customer-ratings (RT-86): the hairdresser rates the customer of a reservation that has ended."""

    RATING_DETAIL = 'The rating must be an integer from 1 to 5.'

    def setUp(self):
        super().setUp()
        self.url = reverse('customer_ratings')
        # The service lasts 30 minutes, so a reservation that started 2 hours ago has ended.
        self.reserve.start_time = timezone.now() - datetime.timedelta(hours=2)
        self.reserve.save()
        self.login_as_hairdresser()

    def _post(self, body, **extra):
        return self.client.post(self.url, data=json.dumps(body), content_type='application/json', **extra)

    def _body(self, **fields):
        return {'reservation': self.reserve.id, 'rating': 4, 'comment': 'Pontual', **fields}

    def _ended_reservation(self):
        start = timezone.now() - datetime.timedelta(hours=2)
        return Reserve.objects.create(customer=self.customer, service=self.service, start_time=start)

    def _pointers(self, response):
        return [item['pointer'] for item in assert_problem(response, 'validation-error')['errors']]

    def test_a_hairdresser_rates_the_customer_of_an_ended_reservation(self):
        """CRT-01"""
        response = self._post(self._body())

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()['data']
        self.assertEqual(set(data), {'id', 'reservation', 'rating', 'comment', 'created_at'})
        created = CustomerRating.objects.get()
        self.assertEqual(
            (data['id'], data['reservation'], data['rating'], data['comment']),
            (created.id, self.reserve.id, 4, 'Pontual'),
        )
        self.assertIsNotNone(data['created_at'])
        self.assertEqual((created.customer_id, created.hairdresser_id), (self.customer.id, self.hairdresser.id))
        self.customer_user.refresh_from_db()
        self.assertEqual(self.customer_user.rating, 4.0)

    def test_a_reservation_that_ends_exactly_now_is_accepted(self):
        """CRT-02"""
        now = timezone.now()
        self.reserve.start_time = now - datetime.timedelta(minutes=30)
        self.reserve.save()

        with patch('django.utils.timezone.now', return_value=now):
            response = self._post(self._body())

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(CustomerRating.objects.filter(reservation=self.reserve).exists())

    def test_a_reservation_that_has_not_ended_answers_409(self):
        """CRT-03"""
        now = timezone.now()
        starts = {
            'ends in 1 minute': now - datetime.timedelta(minutes=29),
            'started 10 minutes ago': now - datetime.timedelta(minutes=10),
            'starts tomorrow': now + datetime.timedelta(days=1),
        }
        for case, start in starts.items():
            with self.subTest(case=case):
                self.reserve.start_time = start
                self.reserve.save()

                with patch('django.utils.timezone.now', return_value=now):
                    response = self._post(self._body())

                assert_problem(
                    response, 'service-not-finished', detail='The service of this reservation has not finished yet.'
                )
                self.assertFalse(CustomerRating.objects.exists())

    def test_a_reservation_without_a_start_time_answers_409(self):
        """CRT-04"""
        self.reserve.start_time = None
        self.reserve.save()

        assert_problem(self._post(self._body()), 'service-not-finished')
        self.assertFalse(CustomerRating.objects.exists())

    def test_a_second_rating_answers_409_and_keeps_the_first(self):
        """CRT-05"""
        self._post(self._body(rating=5, comment='Primeira'))

        response = self._post(self._body(rating=1, comment='Segunda'))

        assert_problem(response, 'review-exists', detail='This reservation has already been rated.')
        rating = CustomerRating.objects.get()
        self.assertEqual((rating.rating, rating.comment), (5, 'Primeira'))
        self.customer_user.refresh_from_db()
        self.assertEqual(self.customer_user.rating, 5.0)

    def test_a_duplicate_that_passes_the_check_answers_409_not_500(self):
        """CRT-06: the unique reservation in the database is what stops the second request of a race."""
        record_customer_rating(self.hairdresser, self.reserve, 5, None)

        with patch('review.views._is_rated', return_value=False):
            response = self._post(self._body(rating=1))

        assert_problem(response, 'review-exists', detail='This reservation has already been rated.')
        self.assertEqual(CustomerRating.objects.get().rating, 5)
        self.customer_user.refresh_from_db()
        self.assertEqual(self.customer_user.rating, 5.0)

    def test_the_reservation_of_another_hairdresser_answers_403(self):
        """CRT-07"""
        other = dict(self.hairdresser_payload, email='other.hairdresser@example.com', phone='+5592984509999')
        self.client.post(self.register_url, data=other)
        activate_account(other['email'])
        self.client.post(
            self.login_url, data=json.dumps({'email': other['email'], 'password': other['password']}),
            content_type='application/json',
        )

        assert_problem(self._post(self._body()), 'forbidden')
        self.assertFalse(CustomerRating.objects.exists())

    def test_a_reservation_that_does_not_exist_answers_404(self):
        """CRT-08"""
        assert_problem(self._post(self._body(reservation=999999)), 'not-found', detail='Reservation not found.')

    def test_no_session_answers_401(self):
        """CRT-09"""
        self.client.cookies.clear()

        assert_problem(self._post(self._body()), 'invalid-session')
        self.assertFalse(CustomerRating.objects.exists())

    def test_a_customer_session_answers_403(self):
        """CRT-10"""
        self.client.cookies.clear()
        self.login_as_customer()

        assert_problem(self._post(self._body()), 'hairdresser-required')
        self.assertFalse(CustomerRating.objects.exists())

    def test_a_rating_that_is_not_an_integer_from_1_to_5_answers_400(self):
        """CRT-11"""
        for value in (4.5, '5', True, 0, 6):
            with self.subTest(rating=value):
                response = self._post(self._body(rating=value))

                assert_problem(response, 'validation-error', errors=[
                    {'pointer': '#/rating', 'detail': self.RATING_DETAIL},
                ])
        body = self._body()
        del body['rating']
        assert_problem(self._post(body), 'validation-error', errors=[
            {'pointer': '#/rating', 'detail': 'This field is required.'},
        ])
        self.assertFalse(CustomerRating.objects.exists())

    def test_a_missing_or_non_integer_reservation_answers_400(self):
        """CRT-12"""
        body = self._body()
        del body['reservation']
        assert_problem(self._post(body), 'validation-error', errors=[
            {'pointer': '#/reservation', 'detail': 'This field is required.'},
        ])
        assert_problem(self._post(self._body(reservation='abc')), 'validation-error', errors=[
            {'pointer': '#/reservation', 'detail': 'This field must be an integer.'},
        ])
        self.assertFalse(CustomerRating.objects.exists())

    def test_a_comment_that_is_not_a_string_or_too_long_answers_400(self):
        """CRT-13"""
        cases = {
            7: 'The comment must be a string.',
            'a' * 501: 'The comment must have at most 500 characters.',
        }
        for value, detail in cases.items():
            with self.subTest(comment=str(value)[:10]):
                assert_problem(self._post(self._body(comment=value)), 'validation-error', errors=[
                    {'pointer': '#/comment', 'detail': detail},
                ])
        self.assertFalse(CustomerRating.objects.exists())

    def test_a_comment_of_500_characters_after_the_trim_is_accepted(self):
        """CRT-13 and CRT-14"""
        response = self._post(self._body(comment='  ' + 'a' * 500 + '  '))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CustomerRating.objects.get().comment, 'a' * 500)

    def test_an_absent_null_or_blank_comment_is_stored_as_null(self):
        """CRT-14"""
        bodies = {'absent': self._body(), 'null': self._body(comment=None), 'blank': self._body(comment='   ')}
        del bodies['absent']['comment']
        for case, body in bodies.items():
            with self.subTest(case=case):
                body['reservation'] = self._ended_reservation().id

                response = self._post(body)

                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                self.assertIsNone(response.json()['data']['comment'])
                self.assertIsNone(CustomerRating.objects.get(reservation_id=body['reservation']).comment)

    def test_a_comment_is_stored_without_the_surrounding_spaces(self):
        """CRT-14"""
        response = self._post(self._body(comment='  ok  '))

        self.assertEqual(response.json()['data']['comment'], 'ok')
        self.assertEqual(CustomerRating.objects.get().comment, 'ok')

    def test_every_invalid_field_is_reported_in_the_same_400(self):
        """CRT-15"""
        response = self._post({'reservation': 'abc', 'rating': 9})

        self.assertEqual(self._pointers(response), ['#/reservation', '#/rating'])

    def test_a_body_that_is_not_a_json_object_answers_400(self):
        """CRT-16"""
        assert_problem(self._post([]), 'malformed-request', detail='The request body must be a JSON object.')
        self.assertFalse(CustomerRating.objects.exists())

    def test_invalid_input_is_reported_before_the_reservation_is_looked_up(self):
        """CRT-17: an unknown reservation with an invalid rating is a 400, not a 404."""
        response = self._post({'reservation': 999999, 'rating': 0})

        self.assertEqual(self._pointers(response), ['#/rating'])

    def test_a_reservation_rebooked_after_a_rated_one_was_cancelled_can_be_rated(self):
        """Edge case of CRT-24: the cancelled reservation's rating keeps no hold on the slot."""
        self.assertEqual(self._post(self._body(rating=5)).status_code, status.HTTP_201_CREATED)
        cancelled = self.client.delete(reverse('reservation_detail', args=[self.reserve.id]))
        self.assertEqual(cancelled.status_code, status.HTTP_204_NO_CONTENT)
        rebooked = Reserve.objects.create(
            customer=self.customer, service=self.service, start_time=self.reserve.start_time,
        )

        response = self._post(self._body(reservation=rebooked.id, rating=3))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            set(CustomerRating.objects.values_list('reservation_id', 'rating')), {(rebooked.id, 3), (None, 5)},
        )
        self.customer_user.refresh_from_db()
        self.assertEqual(self.customer_user.rating, 4.0)

    def test_other_methods_answer_405_with_the_allow_header(self):
        """CRT-55"""
        for method in ('get', 'put', 'delete'):
            with self.subTest(method=method):
                response = getattr(self.client, method)(self.url)

                assert_problem(response, 'method-not-allowed')
                self.assertEqual(sorted(response['Allow'].split(', ')), ['OPTIONS', 'POST'])


class ListCustomerRatingsTest(ReviewsTestCase):
    """GET /api/customers/{id}/ratings (RT-87): average and count for hairdressers, comments for their writers."""

    def setUp(self):
        super().setUp()
        other = dict(
            self.hairdresser_payload, email='other.hairdresser@example.com', phone='+5592984509999',
            first_name='Outra', last_name='Cabeleireira',
        )
        self.client.post(self.register_url, data=other)
        activate_account(other['email'])
        self.other_hairdresser = Hairdresser.objects.get(user__email=other['email'])
        other_service = Service.objects.create(
            name='Escova', price=40.00, hairdresser=self.other_hairdresser, duration=45,
        )
        self.other_reserve = Reserve.objects.create(customer=self.customer, service=other_service)
        self.first = record_customer_rating(self.hairdresser, self.reserve, 5, 'Pontual')
        self.second = record_customer_rating(self.other_hairdresser, self.other_reserve, 4, None)
        self.url = reverse('customer_ratings_by_customer', args=[self.customer.id])

    def _login(self, email, password='Password123'):
        self.client.cookies.clear()
        self.client.post(
            self.login_url, data=json.dumps({'email': email, 'password': password}), content_type='application/json',
        )

    def _ids(self, response):
        return [item['id'] for item in response.json()['data']['ratings']]

    def test_the_customer_sees_every_rating_most_recent_first(self):
        """CRT-28: by created_at, so the older id comes first once it is the newer rating."""
        CustomerRating.objects.filter(id=self.first.id).update(
            created_at=timezone.now() + datetime.timedelta(hours=1)
        )
        self.login_as_customer()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['data']['count'], 2)
        self.assertEqual(self._ids(response), [self.first.id, self.second.id])

    def test_each_hairdresser_sees_the_count_the_average_and_only_their_own_ratings(self):
        """CRT-29"""
        for email, own in (
            (self.hairdresser_payload['email'], self.first),
            ('other.hairdresser@example.com', self.second),
        ):
            with self.subTest(hairdresser=email):
                self._login(email)

                response = self.client.get(self.url)

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                data = response.json()['data']
                self.assertEqual((data['average'], data['count']), (4.5, 2))
                self.assertEqual(self._ids(response), [own.id])

    def test_another_customer_answers_403(self):
        """CRT-30"""
        self._login(self.customer2_payload['email'])

        assert_problem(self.client.get(self.url), 'forbidden')

    def test_a_customer_that_does_not_exist_answers_404(self):
        """CRT-31"""
        self.login_as_hairdresser()

        response = self.client.get(reverse('customer_ratings_by_customer', args=[999999]))

        assert_problem(response, 'not-found', detail='Customer not found.')

    def test_no_session_answers_401(self):
        """CRT-32"""
        assert_problem(self.client.get(self.url), 'invalid-session')

    def test_each_item_has_the_rating_the_comment_the_service_and_the_hairdresser(self):
        """CRT-33"""
        self.login_as_customer()

        items = {item['id']: item for item in self.client.get(self.url).json()['data']['ratings']}

        first = items[self.first.id]
        self.assertEqual(set(first), {'id', 'rating', 'comment', 'created_at', 'service_name', 'hairdresser_name'})
        self.assertEqual(
            (first['rating'], first['comment'], first['service_name'], first['hairdresser_name']),
            (5, 'Pontual', 'Test Service', 'Test Hairdresser'),
        )
        self.assertIsNotNone(first['created_at'])
        second = items[self.second.id]
        self.assertEqual(
            (second['rating'], second['comment'], second['service_name'], second['hairdresser_name']),
            (4, None, 'Escova', 'Outra Cabeleireira'),
        )

    def test_the_names_are_null_once_the_reservation_or_the_author_is_gone(self):
        """CRT-33"""
        self.login_as_customer()
        self.client.delete(reverse('reservation_detail', args=[self.reserve.id]))
        self._login('other.hairdresser@example.com')
        self.assertEqual(self.client.delete(reverse('current_user')).status_code, status.HTTP_204_NO_CONTENT)
        self.login_as_customer()

        items = {item['id']: item for item in self.client.get(self.url).json()['data']['ratings']}

        self.assertEqual(
            (items[self.first.id]['service_name'], items[self.first.id]['hairdresser_name']),
            (None, 'Test Hairdresser'),
        )
        self.assertIsNone(items[self.second.id]['hairdresser_name'])

    def test_a_customer_without_ratings_gets_null_zero_and_an_empty_list(self):
        """CRT-34"""
        self._login(self.customer2_payload['email'])

        response = self.client.get(reverse('customer_ratings_by_customer', args=[self.customer2.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'data': {'average': None, 'count': 0, 'ratings': []}})

    def test_a_pending_customer_is_answered_like_any_other(self):
        """Edge case: a customer who has not confirmed the e-mail is 200 with no ratings for a hairdresser, 403 for another customer."""
        pending = dict(self.customer2_payload, email='pending@example.com', phone='+5592984507777', cpf='12345678999')
        self.client.post(self.register_url, data=pending)
        customer = Customer.objects.get(user__email='pending@example.com')
        self.assertFalse(customer.user.is_active)
        url = reverse('customer_ratings_by_customer', args=[customer.id])

        self.login_as_hairdresser()
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {'data': {'average': None, 'count': 0, 'ratings': []}})

        self.login_as_customer()
        assert_problem(self.client.get(url), 'forbidden')

    def test_the_average_is_the_stored_user_rating(self):
        """CRT-35: a stored value that differs from the rows shows it is read, not recomputed."""
        User.objects.filter(pk=self.customer_user.pk).update(rating=4.33)
        self.login_as_hairdresser()

        response = self.client.get(self.url)

        self.assertEqual(response.json()['data']['average'], 4.33)

    def test_other_methods_answer_405_with_the_allow_header(self):
        """CRT-55"""
        self.login_as_customer()

        response = self.client.post(self.url, data=json.dumps({}), content_type='application/json')

        assert_problem(response, 'method-not-allowed')
        self.assertEqual(sorted(response['Allow'].split(', ')), ['GET', 'HEAD', 'OPTIONS'])


class ReviewPictureModelTest(ReviewsTestCase):
    def setUp(self):
        super().setUp()
        self.review = Review.objects.create(rating=5, customer=self.customer, hairdresser=self.hairdresser)

    def _add(self, name='Foto.PNG', review=None):
        return ReviewPicture.objects.create(review=review or self.review, picture=make_upload(name, fmt='PNG'))

    def test_the_picture_is_stored_under_its_review_as_a_webp(self):
        """REV-02"""
        picture = self._add('Foto.PNG')

        self.assertRegex(picture.picture.name, rf'^reviews/{self.review.id}/[0-9a-f]{{32}}\.webp$')
        with default_storage.open(picture.picture.name) as stored:
            self.assertEqual(Image.open(BytesIO(stored.read())).format, 'WEBP')

    def test_two_pictures_with_the_same_file_name_get_different_keys(self):
        """REV-02"""
        first, second = self._add('foto.png'), self._add('foto.png')

        self.assertNotEqual(first.picture.name, second.picture.name)
        self.assertTrue(default_storage.exists(first.picture.name))
        self.assertTrue(default_storage.exists(second.picture.name))

    def test_the_pictures_of_a_review_come_by_ascending_id(self):
        """REV-33"""
        ids = [self._add().id for _ in range(3)]
        other = Review.objects.create(rating=3, customer=self.customer, hairdresser=self.hairdresser)
        self._add(review=other)

        self.assertEqual([p.id for p in self.review.pictures.all()], ids)
        self.assertEqual(ids, sorted(ids))

    def test_deleting_the_review_deletes_its_pictures(self):
        """REV-33"""
        self._add()
        self._add()
        other = Review.objects.create(rating=3, customer=self.customer, hairdresser=self.hairdresser)
        kept = self._add(review=other)

        self.review.delete()

        self.assertEqual(list(ReviewPicture.objects.values_list('id', flat=True)), [kept.id])


class PictureErrorsTest(SimpleTestCase):
    """REV-04, REV-05, REV-11, REV-12, REV-13"""

    @staticmethod
    def _files(count, size=100):
        return [SimpleNamespace(size=size) for _ in range(count)]

    def test_no_files_are_only_an_error_when_required(self):
        self.assertEqual(picture_errors([], required=True), [
            {'pointer': '#/pictures', 'detail': 'This field is required.'},
        ])
        self.assertEqual(picture_errors([]), [])

    def test_more_than_five_files_are_one_error(self):
        too_many = [{'pointer': '#/pictures', 'detail': 'A review can have at most 5 pictures.'}]

        self.assertEqual(picture_errors(self._files(6)), too_many)
        self.assertEqual(picture_errors(self._files(2), existing=4), too_many)
        self.assertEqual(picture_errors(self._files(5), existing=0), [])
        self.assertEqual(picture_errors(self._files(1), existing=4), [])

    def test_a_file_over_5_mb_is_one_error_and_exactly_5_mb_passes(self):
        too_big = [{'pointer': '#/pictures', 'detail': 'Each picture must have at most 5 MB.'}]

        self.assertEqual(REVIEW_PICTURE_MAX_SIZE, 5 * 1024 * 1024)
        self.assertEqual(picture_errors(self._files(1, size=5 * 1024 * 1024 + 1)), too_big)
        self.assertEqual(picture_errors(self._files(1, size=5 * 1024 * 1024)), [])

    def test_the_first_applicable_error_is_the_only_one_by_the_required_limit_size_order(self):
        big_and_many = self._files(6, size=REVIEW_PICTURE_MAX_SIZE + 1)

        errors = picture_errors(big_and_many)
        self.assertEqual(errors, [{'pointer': '#/pictures', 'detail': 'A review can have at most 5 pictures.'}])
        self.assertEqual(picture_errors([], required=True)[0]['detail'], 'This field is required.')

    def test_no_file_is_opened(self):
        files = [MagicMock(size=REVIEW_PICTURE_MAX_SIZE + 1) for _ in range(2)]

        picture_errors(files)

        for file in files:
            file.open.assert_not_called()
            file.read.assert_not_called()
            file.seek.assert_not_called()


class ReviewPicturesDomainTest(ReviewsTestCase):
    def setUp(self):
        super().setUp()
        self.review = Review.objects.create(rating=5, customer=self.customer, hairdresser=self.hairdresser)

    def test_a_failure_keeps_the_names_already_stored_in_the_list_of_the_caller(self):
        """REV-06, REV-14"""
        saved = []
        files = [make_upload('a.png', fmt='PNG'), make_upload('b.png', fmt='PNG'),
                 SimpleUploadedFile('c.png', b'not an image', content_type='image/png')]

        with self.assertRaises(InvalidImage), transaction.atomic():
            add_review_pictures(self.review, files, saved)

        self.assertEqual(len(saved), 2)
        self.assertEqual(ReviewPicture.objects.count(), 0)  # the savepoint of the view's atomic block is rolled back
        for name in saved:
            self.assertRegex(name, rf'^reviews/{self.review.id}/[0-9a-f]{{32}}\.webp$')
            self.assertTrue(default_storage.exists(name))

    def test_the_pictures_are_stored_in_the_order_received(self):
        saved = []

        add_review_pictures(self.review, [make_upload('a.png', fmt='PNG'), make_upload('b.png', fmt='PNG')], saved)

        self.assertEqual(saved, [p.picture.name for p in self.review.pictures.all()])

    def test_picture_names_are_the_names_of_the_pictures_of_the_queryset(self):
        other = Review.objects.create(rating=3, customer=self.customer, hairdresser=self.hairdresser)
        mine = [ReviewPicture.objects.create(review=self.review, picture=make_upload(fmt='PNG')) for _ in range(2)]
        ReviewPicture.objects.create(review=other, picture=make_upload(fmt='PNG'))

        self.assertEqual(picture_names(self.review.pictures.all()), [p.picture.name for p in mine])
        self.assertEqual(MAX_REVIEW_PICTURES, 5)
