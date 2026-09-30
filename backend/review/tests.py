from hairmatch.problem_testing import assert_problem
from io import BytesIO
from django.core.files.storage import default_storage
from django.test import TestCase
from django.urls import reverse, NoReverseMatch
from rest_framework.test import APIClient
from rest_framework import status
from django.core.files.uploadedfile import SimpleUploadedFile
from unittest.mock import patch
from PIL import Image
from hairmatch.image_fixtures import make_upload
from users.models import User, Customer, Hairdresser
from .models import Review
from reserve.models import Reserve
from service.models import Service
import jwt
import json
import datetime
from django.conf import settings
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
            reserve=Reserve.objects.get(id=self.reserve.id),
        )
        review_raw.save()
    
        # Get the created review and link it to the reserve to test unlinking
        self.review = Review.objects.first()
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
