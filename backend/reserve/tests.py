from unittest.mock import patch

from django.db import connection
from django.test import SimpleTestCase, TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
import json
from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from django.utils import timezone

from users.models import User, Customer, Hairdresser
from service.models import Service
from reserve.models import Reserve
from review.models import Review, ReviewPicture
from hairmatch.image_fixtures import make_upload
from django.core.files.storage import default_storage
from agenda.models import Agenda
from availability.models import Availability
from users.cognito import get_cognito
from hairmatch.local_time import make_local_aware
from hairmatch.problem_testing import assert_problem


class ReserveTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # URLs
        self.create_url = reverse('reservation_collection')
        self.list_url = reverse('reservation_collection')
        self.remove_url = lambda reserve_id: reverse('reservation_detail', args=[reserve_id])
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
            role="customer",
            cognito_sub="sub-customer-1",
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
            role="hairdresser",
            cognito_sub="sub-hairdresser-1",
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

        # A second customer and a second hairdresser, to try each other's resources
        self.other_customer_user = User.objects.create(
            email="other.customer@example.com", first_name="Other", last_name="Customer",
            phone="+5592984503333", neighborhood="Downtown", city="Manaus", state="AM",
            address="Other Street", postal_code="69050750", role="customer",
            cognito_sub="sub-customer-2",
        )
        self.other_customer = Customer.objects.create(user=self.other_customer_user, cpf="12345678902")
        self.other_hairdresser_user = User.objects.create(
            email="other.hairdresser@example.com", first_name="Other", last_name="Hairdresser",
            phone="+5592984504444", neighborhood="Downtown", city="Manaus", state="AM",
            address="Other Street", postal_code="69050750", role="hairdresser",
            cognito_sub="sub-hairdresser-2",
        )
        self.other_hairdresser = Hairdresser.objects.create(user=self.other_hairdresser_user, cnpj="12345678901213")
        self.other_service = Service.objects.create(
            name="Beard", description="Beard trim", price=30.00, duration=30,
            hairdresser=self.other_hairdresser,
        )

    def login(self, user):
        self.client.cookies['jwt'] = get_cognito().client.make_access_token(user.cognito_sub)

    def logout(self):
        self.client.cookies.pop('jwt', None)


class CreateReserveTest(ReserveTestCase):
    def setUp(self):
        super().setUp()
        self.login(self.customer_user)

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
        
        assert_problem(
            response, 'slot-unavailable', detail='The hairdresser is not available during this time slot.'
        )
        self.assertEqual(Reserve.objects.count(), 1)  # No new reserve created
        
    def test_create_reserve_ignores_the_customer_in_the_body(self):
        """The reserve belongs to the session customer, whatever `customer` the body sends"""
        new_start_time = self.reserve_start_time + timedelta(hours=2)

        reserve_data = {
            'start_time': new_start_time.isoformat(),
            'customer': self.other_customer.id,
            'hairdresser': self.hairdresser.id,
            'service': self.service.id
        }

        response = self.client.post(
            self.create_url,
            data=json.dumps(reserve_data),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Reserve.objects.exclude(id=self.reserve.id).get()
        self.assertEqual(created.customer, self.customer)
        self.assertEqual(created.service, self.service)
        self.assertFalse(Reserve.objects.filter(customer=self.other_customer).exists())

    def _post(self, body, **extra):
        if not isinstance(body, str):
            body = json.dumps(body)
        return self.client.post(self.create_url, data=body, content_type='application/json', **extra)

    def _payload(self, **overrides):
        payload = {
            'start_time': (self.reserve_start_time + timedelta(hours=2)).isoformat(),
            'hairdresser': self.hairdresser.id,
            'service': self.service.id,
        }
        payload.update(overrides)
        return payload

    def test_create_reserve_with_a_body_that_is_not_json_answers_400_without_the_exception_text(self):
        for raw in ('{nope', '[1]', '"text"'):
            with self.subTest(raw=raw):
                response = self._post(raw)

                body = assert_problem(response, 'malformed-request')
                self.assertNotIn('Expecting', body['detail'])
        self.assertEqual(Reserve.objects.count(), 1)

    def test_create_reserve_reports_every_missing_field(self):
        response = self._post({})

        assert_problem(response, 'validation-error', errors=[
            {'pointer': '#/hairdresser', 'detail': 'This field is required.'},
            {'pointer': '#/service', 'detail': 'This field is required.'},
            {'pointer': '#/start_time', 'detail': 'This field is required.'},
        ])

    def test_create_reserve_with_ids_that_are_not_integers_answers_400(self):
        response = self._post(self._payload(hairdresser='abc', service=[1]))

        assert_problem(response, 'validation-error', errors=[
            {'pointer': '#/hairdresser', 'detail': 'This field must be an integer.'},
            {'pointer': '#/service', 'detail': 'This field must be an integer.'},
        ])

    def test_create_reserve_with_a_start_time_that_is_not_iso_8601_answers_400(self):
        for start_time in ('tomorrow at 3pm', '2025-13-45T10:00:00', 12345):
            with self.subTest(start_time=start_time):
                response = self._post(self._payload(start_time=start_time))

                assert_problem(response, 'validation-error', errors=[{
                    'pointer': '#/start_time',
                    'detail': "The start time must be an ISO 8601 datetime like '2025-04-26T14:30:00Z'.",
                }])
        self.assertEqual(Reserve.objects.count(), 1)

    def test_create_reserve_that_clashes_with_another_reserve_of_the_customer_answers_409(self):
        payload = self._payload(
            hairdresser=self.other_hairdresser.id, service=self.other_service.id,
            start_time=(self.reserve_start_time + timedelta(minutes=30)).isoformat(),
        )

        response = self._post(payload)

        assert_problem(
            response, 'customer-schedule-conflict', detail='You already have another reservation at the same time.'
        )
        self.assertEqual(Reserve.objects.count(), 1)
        self.assertFalse(Agenda.objects.filter(hairdresser=self.other_hairdresser).exists())

    def test_create_reserve_that_fails_to_save_answers_500_and_rolls_back(self):
        with patch.object(Agenda.objects, 'create', side_effect=RuntimeError('disk on fire')):
            with self.assertLogs('hairmatch.problems', level='ERROR'):
                response = self._post(self._payload())

        body = assert_problem(response, 'internal-error', detail='An unexpected error occurred.')
        self.assertNotIn('disk on fire', json.dumps(body))
        self.assertEqual(Reserve.objects.count(), 1)

    def test_create_reserve_without_session_is_refused_with_401(self):
        self.logout()
        reserve_data = {
            'start_time': (self.reserve_start_time + timedelta(hours=2)).isoformat(),
            'customer': self.customer.id,
            'hairdresser': self.hairdresser.id,
            'service': self.service.id
        }

        response = self.client.post(self.create_url, data=json.dumps(reserve_data), content_type='application/json')

        assert_problem(response, 'invalid-session')
        self.assertEqual(Reserve.objects.count(), 1)
        self.assertEqual(Agenda.objects.count(), 1)

    def test_create_reserve_as_hairdresser_is_refused_with_403(self):
        self.login(self.hairdresser_user)
        reserve_data = {
            'start_time': (self.reserve_start_time + timedelta(hours=2)).isoformat(),
            'hairdresser': self.hairdresser.id,
            'service': self.service.id
        }

        response = self.client.post(self.create_url, data=json.dumps(reserve_data), content_type='application/json')

        assert_problem(response, 'customer-required', detail='Only customers can perform this action.')
        self.assertEqual(Reserve.objects.count(), 1)

    def test_create_reserve_with_a_service_of_another_hairdresser_is_refused(self):
        """The agenda block must land on the hairdresser who owns the service"""
        reserve_data = {
            'start_time': (self.reserve_start_time + timedelta(hours=2)).isoformat(),
            'hairdresser': self.hairdresser.id,
            'service': self.other_service.id
        }

        response = self.client.post(self.create_url, data=json.dumps(reserve_data), content_type='application/json')

        assert_problem(response, 'validation-error', errors=[
            {'pointer': '#/service', 'detail': 'The service does not belong to this hairdresser.'}
        ])
        self.assertEqual(Reserve.objects.count(), 1)
        self.assertEqual(Agenda.objects.count(), 1)
        
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
        
        assert_problem(response, 'not-found', detail='Hairdresser not found.')
        
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
        
        assert_problem(response, 'not-found', detail='Service not found.')


class ListReserveTest(ReserveTestCase):
    def setUp(self):
        super().setUp()
        # A reserve of another customer, which must never show up in the lists below
        Reserve.objects.create(
            start_time=self.reserve_start_time, customer=self.other_customer, service=self.other_service
        )

    def test_list_without_id_returns_only_the_session_customer_reserves(self):
        self.login(self.customer_user)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([r['id'] for r in response.json()['data']], [self.reserve.id])

    def test_list_user_reserves(self):
        """Test listing reserves for a specific user"""
        self.login(self.customer_user)
        list_user_url = reverse('customer_reservations', args=[self.customer.id])

        response = self.client.get(list_user_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([r['id'] for r in response.json()['data']], [self.reserve.id])

    def test_list_reserves_of_another_customer_is_refused_with_403(self):
        self.login(self.other_customer_user)

        response = self.client.get(reverse('customer_reservations', args=[self.customer.id]))

        assert_problem(response, 'forbidden')
        self.assertNotIn('data', response.json())

    def test_list_without_session_is_refused_with_401(self):
        for url in (self.list_url, reverse('customer_reservations', args=[self.customer.id])):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ReserveByIdTest(ReserveTestCase):
    def url(self, reserve_id):
        return reverse('reservation_detail', args=[reserve_id])

    def test_reading_a_reserve_that_does_not_exist_answers_404(self):
        self.login(self.customer_user)

        response = self.client.get(self.url(9999))

        assert_problem(response, 'not-found', detail='Reservation not found.')

    def test_customer_reads_own_reserve(self):
        self.login(self.customer_user)

        response = self.client.get(self.url(self.reserve.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['data']['id'], self.reserve.id)

    def test_hairdresser_of_the_service_reads_the_reserve(self):
        self.login(self.hairdresser_user)

        response = self.client.get(self.url(self.reserve.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_other_customer_and_other_hairdresser_are_refused_with_403(self):
        for user in (self.other_customer_user, self.other_hairdresser_user):
            with self.subTest(user=user.email):
                self.login(user)
                response = self.client.get(self.url(self.reserve.id))
                assert_problem(response, 'forbidden')
                self.assertNotIn('data', response.json())

    def test_without_session_is_refused_with_401(self):
        response = self.client.get(self.url(self.reserve.id))

        assert_problem(response, 'invalid-session')


class RemoveReserveTest(ReserveTestCase):
    def test_remove_reserve_success(self):
        """Test successful reserve removal"""
        self.login(self.customer_user)
        response = self.client.delete(self.remove_url(self.reserve.id))
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.content, b'')
        self.assertEqual(Reserve.objects.count(), 0)
        
    def test_hairdresser_of_the_service_removes_the_reserve(self):
        self.login(self.hairdresser_user)

        response = self.client.delete(self.remove_url(self.reserve.id))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Reserve.objects.exists())

    def test_remove_nonexistent_reserve(self):
        """Test removing a non-existent reserve"""
        self.login(self.customer_user)
        response = self.client.delete(self.remove_url(9999))  # Non-existent ID
        assert_problem(response, 'not-found', detail='Reservation not found.')

    def test_remove_reserve_of_someone_else_is_refused_with_403(self):
        for user in (self.other_customer_user, self.other_hairdresser_user):
            with self.subTest(user=user.email):
                self.login(user)
                response = self.client.delete(self.remove_url(self.reserve.id))
                assert_problem(response, 'forbidden')
                self.assertTrue(Reserve.objects.filter(id=self.reserve.id).exists())

    def test_remove_without_session_is_refused_with_401(self):
        response = self.client.delete(self.remove_url(self.reserve.id))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertTrue(Reserve.objects.filter(id=self.reserve.id).exists())
        self.assertTrue(Agenda.objects.filter(id=self.agenda.id).exists())

    def test_cancelling_frees_the_agenda_slot_and_keeps_the_hairdressers_other_blocks(self):
        manual_block = Agenda.objects.create(
            start_time=self.reserve_start_time + timedelta(hours=3),
            end_time=self.reserve_start_time + timedelta(hours=4),
            hairdresser=self.hairdresser,
            service=self.service,
        )
        self.login(self.customer_user)

        response = self.client.delete(self.remove_url(self.reserve.id))

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Agenda.objects.filter(id=self.agenda.id).exists())
        self.assertTrue(Agenda.objects.filter(id=manual_block.id).exists())

    def test_a_cancelled_slot_can_be_booked_again(self):
        today = timezone.now().date()
        next_monday = today + timedelta(days=7 - today.weekday())
        slots_query = {'date': next_monday.strftime('%Y-%m-%d'), 'service': self.service.id}
        self.login(self.customer_user)
        booked = self.client.post(self.create_url, data=json.dumps({
            'hairdresser': self.hairdresser.id,
            'service': self.service.id,
            'start_time': f'{next_monday.isoformat()}T14:00:00',
        }), content_type='application/json')
        self.assertEqual(booked.status_code, status.HTTP_201_CREATED)
        slots = lambda: self.client.get(self.get_slots_url(self.hairdresser.id), slots_query).json()['available_slots']
        self.assertNotIn('14:00', slots())

        reserve = Reserve.objects.get(start_time=make_local_aware(datetime.combine(next_monday, time(14, 0))))
        self.assertEqual(self.client.delete(self.remove_url(reserve.id)).status_code, status.HTTP_204_NO_CONTENT)

        self.assertIn('14:00', slots())


class ReserveSlotTest(ReserveTestCase):
    def get_slots(self, hairdresser_id, **query):
        return self.client.get(self.get_slots_url(hairdresser_id), query)

    def test_get_available_slots(self):
        """RT-63: the slots come from a GET with the service and the date in the query."""
        # Get tomorrow's date which is a Monday (to match our test availability)
        today = timezone.now().date()
        days_ahead = 7 - today.weekday()  # Next Monday
        next_monday = today + timedelta(days=days_ahead)

        response = self.get_slots(self.hairdresser.id, date=next_monday.strftime('%Y-%m-%d'), service=self.service.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(list(response.json()), ['available_slots'])
        # Monday's availability is 09:00 to 17:00 and the service lasts an hour or less.
        self.assertIn('09:00', response.json()['available_slots'])

    def test_get_slots_without_service_and_date_reports_both(self):
        """RT-64: each missing parameter is a `parameter` item, not a body pointer."""
        response = self.get_slots(self.hairdresser.id)

        assert_problem(response, 'validation-error', errors=[
            {'parameter': 'service', 'detail': 'This field is required.'},
            {'parameter': 'date', 'detail': 'This field is required.'},
        ])

    def test_get_slots_with_a_missing_service_and_a_bad_date_reports_each_parameter(self):
        response = self.get_slots(self.hairdresser.id, date='26/04/2025')

        assert_problem(response, 'validation-error', errors=[
            {'parameter': 'service', 'detail': 'This field is required.'},
            {'parameter': 'date', 'detail': 'The date must be in YYYY-MM-DD format.'},
        ])

    def test_get_slots_with_a_service_that_is_not_an_integer_answers_400(self):
        for service in ('abc', '1.5', '--5'):
            with self.subTest(service=service):
                response = self.get_slots(self.hairdresser.id, date='2025-04-28', service=service)

                assert_problem(response, 'validation-error', errors=[
                    {'parameter': 'service', 'detail': 'This field must be an integer.'},
                ])

    def test_get_slots_with_a_repeated_parameter_uses_the_last_value(self):
        """RT-83: `?date=bad&date=<monday>` is read as the Monday."""
        today = timezone.now().date()
        next_monday = today + timedelta(days=7 - today.weekday())
        query = f'service={self.service.id}&date=not-a-date&date={next_monday:%Y-%m-%d}'

        response = self.client.get(f'{self.get_slots_url(self.hairdresser.id)}?{query}')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('09:00', response.json()['available_slots'])

    def test_get_slots_invalid_hairdresser(self):
        """Test getting slots for non-existent hairdresser"""
        today = timezone.now().date()

        response = self.get_slots(9999, date=today.strftime('%Y-%m-%d'), service=self.service.id)

        assert_problem(response, 'not-found', detail='Hairdresser not found.')

    def test_get_slots_invalid_service(self):
        """Test getting slots with non-existent service"""
        today = timezone.now().date()

        response = self.get_slots(self.hairdresser.id, date=today.strftime('%Y-%m-%d'), service=9999)

        assert_problem(response, 'not-found', detail='Service not found.')

    def test_get_slots_invalid_date_format(self):
        """Test getting slots with invalid date format"""
        response = self.get_slots(self.hairdresser.id, date='invalid-date', service=self.service.id)

        assert_problem(response, 'validation-error', errors=[
            {'parameter': 'date', 'detail': 'The date must be in YYYY-MM-DD format.'}
        ])

    def test_get_slots_no_availability(self):
        """Test getting slots when hairdresser has no availability for that day"""
        # Create a date for Tuesday, when we have no availability set
        today = timezone.now().date()
        days_ahead = (1 - today.weekday()) % 7 + 1  # Next Tuesday
        next_tuesday = today + timedelta(days=days_ahead)

        response = self.get_slots(self.hairdresser.id, date=next_tuesday.strftime('%Y-%m-%d'), service=self.service.id)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['available_slots'], [])

def next_monday():
    today = timezone.now().date()
    return today + timedelta(days=7 - today.weekday())


def reserve_views():
    # Imported late: importing reserve.views before users.serializers hits the users/service serializers import cycle
    from reserve import views
    return views


class GenerateTimeSlotsTest(SimpleTestCase):
    DAY = date(2026, 10, 5)

    def test_the_last_slot_is_closing_time_minus_the_service_duration(self):
        slots = reserve_views().generate_time_slots(self.DAY, time(9, 0), time(17, 0), [], 60)

        self.assertEqual(slots[0], '09:00')
        self.assertEqual(slots[-1], '16:00')
        self.assertNotIn('16:30', slots)

    def test_no_slot_overlaps_the_break(self):
        slots = reserve_views().generate_time_slots(self.DAY, time(9, 0), time(17, 0), [], 60, time(12, 0), time(13, 0))

        self.assertIn('11:00', slots)
        for slot in ('11:30', '12:00', '12:30'):
            self.assertNotIn(slot, slots)
        self.assertIn('13:00', slots)
        self.assertEqual(slots[-1], '16:00')


class ReserveInManausTimeTest(ReserveTestCase):
    """The app and the chatbot send the slot as a naive Manaus time (UTC-4), the clock the slots are listed in."""

    def get_slots(self, hairdresser, service, day):
        response = self.client.get(
            self.get_slots_url(hairdresser.id), {'date': day.isoformat(), 'service': service.id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.json()['available_slots']

    def test_a_booked_slot_is_no_longer_listed(self):
        day = next_monday()
        self.login(self.customer_user)

        response = self.client.post(
            self.create_url,
            data=json.dumps({
                'start_time': f'{day.isoformat()}T09:00:00',
                'hairdresser': self.hairdresser.id,
                'service': self.service.id,
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Reserve.objects.exclude(id=self.reserve.id).get()
        self.assertEqual(created.start_time, datetime(day.year, day.month, day.day, 13, 0, tzinfo=dt_timezone.utc))
        slots = self.get_slots(self.hairdresser, self.service, day)
        self.assertNotIn('09:00', slots)
        self.assertNotIn('09:30', slots)
        self.assertIn('10:00', slots)
        self.assertEqual(slots[-1], '16:00')

    def test_a_booking_late_in_the_evening_blocks_its_slot(self):
        """21:00 in Manaus is already the next day in UTC, and still belongs to the Manaus day being listed"""
        day = next_monday()
        Availability.objects.create(
            hairdresser=self.other_hairdresser, weekday='monday',
            start_time=time(18, 0), end_time=time(23, 0),
        )
        start = make_local_aware(datetime.combine(day, time(21, 0)))
        Agenda.objects.create(
            start_time=start, end_time=start + timedelta(minutes=self.other_service.duration),
            hairdresser=self.other_hairdresser, service=self.other_service,
        )

        slots = self.get_slots(self.other_hairdresser, self.other_service, day)

        self.assertIn('20:30', slots)
        self.assertNotIn('21:00', slots)
        self.assertIn('21:30', slots)


class CreateNewReserveTest(ReserveTestCase):
    """The chatbot's booking path"""

    def test_a_clash_with_another_reserve_of_the_customer_is_refused(self):
        clashing_start = self.reserve_start_time + timedelta(minutes=30)

        result = reserve_views().create_new_reserve(self.customer.id, self.other_service.id, self.other_hairdresser.id, clashing_start)

        self.assertEqual(result, {'error': 'Você já tem outra reserva agendada para o mesmo horário'})
        self.assertEqual(Reserve.objects.count(), 1)
        self.assertFalse(Agenda.objects.filter(hairdresser=self.other_hairdresser).exists())

    def test_a_free_slot_is_booked(self):
        start = self.reserve_start_time + timedelta(hours=3)

        result = reserve_views().create_new_reserve(self.customer.id, self.other_service.id, self.other_hairdresser.id, start)

        self.assertTrue(result.get('success'))
        self.assertEqual(result['reserve'].start_time, start)
        agenda = Agenda.objects.get(hairdresser=self.other_hairdresser)
        self.assertEqual(agenda.end_time, start + timedelta(minutes=self.other_service.duration))


class ExternalBlockTest(ReserveTestCase):
    """
    EXT-15 to EXT-17: a block the hairdresser adds by POST /api/agenda leaves the slot offer and refuses bookings.
    Monday's availability runs from 09:00 to 17:00 with a break from 12:00 to 13:00.
    """

    def setUp(self):
        super().setUp()
        self.day = next_monday()

    def add_block(self, start, end, **fields):
        self.login(self.hairdresser_user)
        response = self.client.post(reverse('agenda_collection'), data=json.dumps({
            'start_time': f'{self.day.isoformat()}T{start}:00',
            'end_time': f'{self.day.isoformat()}T{end}:00',
            **fields,
        }), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        self.logout()

    def offered_slots(self):
        response = self.client.get(
            self.get_slots_url(self.hairdresser.id), {'date': self.day.isoformat(), 'service': self.service.id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.json()['available_slots']

    def assert_offer(self, slots, offered, left_out):
        for slot in offered:
            self.assertIn(slot, slots)
        for slot in left_out:
            self.assertNotIn(slot, slots)

    def test_a_block_without_a_service_leaves_the_slot_offer(self):
        """EXT-15: a 60-minute service crossing 10:00-11:00 is not offered"""
        self.assertEqual(self.service.duration, 60)
        self.add_block('10:00', '11:00', title='Cliente do WhatsApp')

        self.assert_offer(self.offered_slots(), offered=('09:00', '11:00'), left_out=('09:30', '10:00', '10:30'))

    def test_a_block_with_a_service_and_an_edited_end_leaves_the_offer_until_that_end(self):
        """EXT-15: 14:00 plus the 60-minute service would end at 15:00, but the block ends at 15:30"""
        self.add_block('14:00', '15:30', service=self.service.id)

        self.assert_offer(
            self.offered_slots(), offered=('13:00', '15:30'), left_out=('13:30', '14:00', '14:30', '15:00')
        )

    def test_the_chatbot_slots_leave_out_the_block_too(self):
        """EXT-16"""
        self.add_block('10:00', '11:00', title='Cliente do WhatsApp')

        result = reserve_views().get_available_slots(self.hairdresser.id, self.service.id, self.day.isoformat())

        self.assert_offer(result['available_slots'], offered=('09:00', '11:00'), left_out=('09:30', '10:00', '10:30'))
        self.assertEqual(result['available_slots'], self.offered_slots())

    def test_a_booking_inside_a_block_without_a_service_answers_409(self):
        """EXT-17"""
        self.add_block('10:00', '11:00', title='Cliente do WhatsApp')
        reserves, agendas = Reserve.objects.count(), Agenda.objects.count()
        self.login(self.customer_user)

        response = self.client.post(self.create_url, data=json.dumps({
            'hairdresser': self.hairdresser.id,
            'service': self.service.id,
            'start_time': f'{self.day.isoformat()}T10:30:00',
        }), content_type='application/json')

        assert_problem(
            response, 'slot-unavailable', detail='The hairdresser is not available during this time slot.'
        )
        self.assertEqual(Reserve.objects.count(), reserves)
        self.assertEqual(Agenda.objects.count(), agendas)


class ReservationReviewPicturesTest(ReserveTestCase):
    """REV-30, REV-32: the review of a reservation carries its pictures in RT-43, RT-45 and RT-46."""

    def _review(self, reserve, pictures):
        review = Review.objects.create(rating=5, customer=self.customer, hairdresser=self.hairdresser)
        for _ in range(pictures):
            ReviewPicture.objects.create(review=review, picture=make_upload(fmt='PNG'))
        reserve.review = review
        reserve.save()
        return review

    def _extra_reviewed_reserves(self, count):
        for _ in range(count):
            reserve = Reserve.objects.create(
                start_time=self.reserve_start_time, customer=self.customer, service=self.service
            )
            self._review(reserve, 2)

    def _expected(self, review):
        return [{'id': p.id, 'url': default_storage.url(p.picture.name)} for p in review.pictures.all()]

    def test_the_three_reads_return_the_pictures_of_the_review(self):
        review = self._review(self.reserve, 2)
        self.login(self.customer_user)
        urls = {
            'RT-43': reverse('reservation_detail', args=[self.reserve.id]),
            'RT-45': self.list_url,
            'RT-46': reverse('customer_reservations', args=[self.customer.id]),
        }

        for name, url in urls.items():
            with self.subTest(route=name):
                data = self.client.get(url).json()['data']
                reserve = data if isinstance(data, dict) else data[0]
                self.assertEqual(len(reserve['review']['pictures']), 2)
                self.assertEqual(reserve['review']['pictures'], self._expected(review))
                self.assertNotIn('picture', reserve['review'])

    def test_a_reservation_without_a_review_keeps_review_null(self):
        self.login(self.customer_user)

        data = self.client.get(reverse('reservation_detail', args=[self.reserve.id])).json()['data']

        self.assertIsNone(data['review'])

    def test_the_customer_list_runs_the_same_number_of_queries_with_one_and_three_reviews(self):
        url = reverse('customer_reservations', args=[self.customer.id])
        self._review(self.reserve, 2)
        self.login(self.customer_user)
        with CaptureQueriesContext(connection) as one:
            self.client.get(url)

        self._extra_reviewed_reserves(2)
        with CaptureQueriesContext(connection) as three:
            data = self.client.get(url).json()['data']

        self.assertEqual([len(r['review']['pictures']) for r in data], [2, 2, 2])
        self.assertEqual(len(three), len(one))
