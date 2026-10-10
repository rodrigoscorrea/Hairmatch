from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
import calendar
import json
from datetime import datetime, time, timedelta, timezone as dt_timezone
from unittest import mock
from django.utils import timezone

from django.db import connection
from django.test.utils import CaptureQueriesContext

from users.models import User, Customer, Hairdresser
from review.customer_ratings import record_customer_rating
from service.models import Service
from agenda.models import Agenda
from availability.models import Availability
from reserve.models import Reserve
from users.cognito import get_cognito
from hairmatch.problem_testing import assert_problem


class AgendaTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # URLs
        self.create_url = reverse('agenda_collection')
        self.list_url = reverse('agenda_collection')
        self.remove_url = lambda agenda_id: reverse('agenda_detail', args=[agenda_id])
        
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
            rating=4.5,
            cognito_sub="sub-hairdresser-1",
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
            rating=4.0,
            cognito_sub="sub-hairdresser-2",
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

    def login(self, user):
        self.client.cookies['jwt'] = get_cognito().client.make_access_token(user.cognito_sub)


def local_iso(day, hour, minute=0):
    """A naive ISO datetime, which the API reads as Manaus time (UTC-4)."""
    return f'{day.isoformat()}T{hour:02d}:{minute:02d}:00'


def manaus_in_utc(day, hour, minute=0):
    """The aware UTC instant of a Manaus wall-clock time."""
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=dt_timezone.utc) + timedelta(hours=4)


class CreateAgendaTest(AgendaTestCase):
    def setUp(self):
        super().setUp()
        self.login(self.hairdresser_user)
        # Two days ahead, clear of the fixture block (tomorrow 10:00 UTC)
        self.day = (timezone.now() + timedelta(days=2)).date()

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
        
    def test_create_agenda_ignores_the_hairdresser_in_the_body(self):
        """The slot is blocked in the session hairdresser's agenda, whatever `hairdresser` the body sends"""
        new_start_time = self.agenda_start_time + timedelta(hours=2)

        agenda_data = {
            'start_time': new_start_time.isoformat(),
            'hairdresser': self.hairdresser2.id,
            'service': self.service.id
        }

        response = self.client.post(self.create_url, data=json.dumps(agenda_data), content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Agenda.objects.exclude(id=self.agenda.id).get()
        self.assertEqual(created.hairdresser, self.hairdresser)
        self.assertFalse(Agenda.objects.filter(hairdresser=self.hairdresser2).exists())

    def test_create_agenda_with_a_service_of_another_hairdresser_is_refused_with_403(self):
        """Otherwise the other hairdresser could never delete that service"""
        other_service = Service.objects.create(
            name="Beard", description="", price=20.00, duration=30, hairdresser=self.hairdresser2
        )
        agenda_data = {
            'start_time': (self.agenda_start_time + timedelta(hours=2)).isoformat(),
            'service': other_service.id
        }

        response = self.client.post(self.create_url, data=json.dumps(agenda_data), content_type='application/json')

        assert_problem(response, 'forbidden')
        self.assertFalse(Agenda.objects.filter(service=other_service).exists())

    def test_create_agenda_without_session_is_refused_with_401(self):
        self.client.cookies.pop('jwt')
        agenda_data = {
            'start_time': (self.agenda_start_time + timedelta(hours=2)).isoformat(),
            'hairdresser': self.hairdresser.id,
            'service': self.service.id
        }

        response = self.client.post(self.create_url, data=json.dumps(agenda_data), content_type='application/json')

        assert_problem(response, 'invalid-session')
        self.assertEqual(Agenda.objects.count(), 1)
        
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
        
        assert_problem(response, 'not-found', detail='Service not found.')
        self.assertEqual(Agenda.objects.count(), 1)
        
    def _post(self, body):
        if not isinstance(body, str):
            body = json.dumps(body)
        return self.client.post(self.create_url, data=body, content_type='application/json')

    def test_create_agenda_that_overlaps_an_existing_block_answers_409(self):
        overlapping = self.agenda_start_time + timedelta(minutes=30)

        response = self._post({'start_time': overlapping.isoformat(), 'service': self.service.id})

        assert_problem(
            response, 'agenda-overlap', detail='This time slot overlaps with an existing appointment.'
        )
        self.assertEqual(Agenda.objects.count(), 1)

    def test_create_agenda_with_an_end_time_that_overlaps_answers_409(self):
        start = self.agenda_start_time - timedelta(hours=1)

        response = self._post({
            'start_time': start.isoformat(),
            'end_time': (self.agenda_start_time + timedelta(minutes=10)).isoformat(),
            'service': self.service.id,
        })

        assert_problem(response, 'agenda-overlap')

    def test_create_agenda_with_a_body_that_is_not_json_answers_400(self):
        for raw in ('{nope', '[1]'):
            with self.subTest(raw=raw):
                assert_problem(self._post(raw), 'malformed-request')

    def test_create_agenda_reports_every_missing_field(self):
        """EXT-14: the service is optional, so an empty body misses the times and the title"""
        response = self._post({})

        assert_problem(response, 'validation-error', errors=[
            {'pointer': '#/start_time', 'detail': 'This field is required.'},
            {'pointer': '#/end_time', 'detail': 'This field is required.'},
            {'pointer': '#/title', 'detail': 'This field is required.'},
        ])
        self.assertEqual(Agenda.objects.count(), 1)

    def test_create_agenda_with_invalid_start_and_end_times_points_at_each_field(self):
        for bad in ('tomorrow', '2025-13-45T10:00:00', 12345):
            with self.subTest(bad=bad):
                response = self._post({'start_time': bad, 'end_time': bad, 'service': self.service.id})

                assert_problem(response, 'validation-error', errors=[
                    {'pointer': '#/start_time', 'detail': 'The value must be an ISO 8601 datetime.'},
                    {'pointer': '#/end_time', 'detail': 'The value must be an ISO 8601 datetime.'},
                ])

    def test_create_agenda_with_only_a_bad_end_time_points_at_that_field(self):
        response = self._post({
            'start_time': (self.agenda_start_time + timedelta(hours=3)).isoformat(),
            'end_time': 'later',
            'service': self.service.id,
        })

        assert_problem(response, 'validation-error', errors=[
            {'pointer': '#/end_time', 'detail': 'The value must be an ISO 8601 datetime.'},
        ])
        self.assertEqual(Agenda.objects.count(), 1)

    def test_create_agenda_with_a_service_id_that_is_not_a_number_answers_404(self):
        response = self._post({
            'start_time': (self.agenda_start_time + timedelta(hours=3)).isoformat(), 'service': 'abc',
        })

        assert_problem(response, 'not-found', detail='Service not found.')

    def test_create_agenda_as_a_customer_answers_403_hairdresser_required(self):
        customer = User.objects.create(
            email='customer@example.com', first_name='C', last_name='U', phone='+5592984509999',
            neighborhood='X', city='Manaus', state='AM', address='Street', postal_code='69050750',
            role='customer', cognito_sub='sub-customer-1',
        )
        self.login(customer)

        response = self._post({'start_time': self.agenda_start_time.isoformat(), 'service': self.service.id})

        assert_problem(response, 'hairdresser-required', detail='Only hairdressers can perform this action.')

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

    def test_create_agenda_with_a_naive_start_time_blocks_it_in_manaus_time(self):
        """A time without offset is the salon's wall clock (UTC-4), not UTC"""
        day = (timezone.now() + timedelta(days=3)).date()
        agenda_data = {'start_time': f'{day.isoformat()}T09:00:00', 'service': self.service.id}

        response = self.client.post(self.create_url, data=json.dumps(agenda_data), content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Agenda.objects.exclude(id=self.agenda.id).get()
        expected_start = datetime(day.year, day.month, day.day, 13, 0, tzinfo=dt_timezone.utc)
        self.assertEqual(created.start_time, expected_start)
        self.assertEqual(created.end_time, expected_start + timedelta(minutes=self.service.duration))

    # External blocks: booked outside the app, with or without one of the hairdresser's services

    def block(self, start_hour, end_hour=None, **fields):
        body = {'start_time': local_iso(self.day, start_hour)}
        if end_hour is not None:
            body['end_time'] = local_iso(self.day, end_hour)
        return {**body, **fields}

    def assert_refused(self, response, pointer, detail):
        assert_problem(response, 'validation-error', errors=[{'pointer': pointer, 'detail': detail}])
        self.assertEqual(Agenda.objects.count(), 1)

    def test_a_block_without_a_service_is_created_with_its_trimmed_title(self):
        """EXT-01"""
        response = self._post(self.block(10, 11, title='  Cliente do WhatsApp  '))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json(), {'message': 'Agenda register created successfully'})
        self.assertEqual(Agenda.objects.count(), 2)
        created = Agenda.objects.exclude(id=self.agenda.id).get()
        self.assertIsNone(created.service_id)
        self.assertEqual(created.title, 'Cliente do WhatsApp')
        self.assertEqual(created.start_time, manaus_in_utc(self.day, 10))
        self.assertEqual(created.end_time, manaus_in_utc(self.day, 11))
        self.assertEqual(created.hairdresser, self.hairdresser)

    def test_a_block_with_a_service_and_no_end_time_lasts_the_service_duration(self):
        """EXT-02, and EXT-04/EXT-07: with a service, neither the title nor the end time is required"""
        for hour, title_field, stored_title in ((10, {}, ''), (14, {'title': ' Maria '}, 'Maria')):
            with self.subTest(title=title_field.get('title')):
                response = self._post(self.block(hour, service=self.service.id, **title_field))

                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                created = Agenda.objects.get(start_time=manaus_in_utc(self.day, hour))
                self.assertEqual(created.service, self.service)
                self.assertEqual(created.end_time, manaus_in_utc(self.day, hour) + timedelta(minutes=60))
                self.assertEqual(created.title, stored_title)

    def test_a_block_with_a_service_keeps_the_end_time_sent(self):
        """EXT-03: the sent end time wins over the start plus the service duration"""
        response = self._post({
            'start_time': local_iso(self.day, 10), 'end_time': local_iso(self.day, 10, 45),
            'service': self.service.id,
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created = Agenda.objects.exclude(id=self.agenda.id).get()
        self.assertEqual(created.service, self.service)
        self.assertEqual(created.end_time, manaus_in_utc(self.day, 10, 45))

    def test_a_block_without_a_service_requires_a_title(self):
        """EXT-04"""
        for title_field in ({}, {'title': ''}, {'title': '   '}):
            with self.subTest(title=title_field.get('title')):
                response = self._post(self.block(10, 11, **title_field))

                self.assert_refused(response, '#/title', 'This field is required.')

    def test_a_title_that_is_not_a_string_is_refused(self):
        """EXT-05"""
        for title in (123, ['x']):
            with self.subTest(title=title):
                response = self._post(self.block(10, 11, title=title))

                self.assert_refused(response, '#/title', 'This field must be a string.')

    def test_a_null_title_is_read_as_an_absent_one(self):
        """EXT-05: null is not "present and not a string"; it falls back to EXT-04 or to an empty title"""
        with self.subTest('without a service'):
            response = self._post(self.block(10, 11, title=None))

            self.assert_refused(response, '#/title', 'This field is required.')

        with self.subTest('with a service'):
            response = self._post(self.block(14, service=self.service.id, title=None))

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertEqual(Agenda.objects.count(), 2)
            created = Agenda.objects.get(start_time=manaus_in_utc(self.day, 14))
            self.assertEqual(created.service, self.service)
            self.assertEqual(created.title, '')

    def test_a_title_over_100_characters_is_refused(self):
        """EXT-06"""
        response = self._post(self.block(10, 11, title='a' * 101))

        self.assert_refused(response, '#/title', 'Ensure this field has no more than 100 characters.')

    def test_a_title_of_100_characters_is_accepted_even_with_surrounding_spaces(self):
        """EXT-06: the limit applies after the strip"""
        for hour, title in ((10, 'a' * 100), (14, f'  {"b" * 100}  ')):
            with self.subTest(length=len(title)):
                response = self._post(self.block(hour, hour + 1, title=title))

                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                created = Agenda.objects.get(start_time=manaus_in_utc(self.day, hour))
                self.assertEqual(created.title, title.strip())

    def test_a_block_without_a_service_requires_an_end_time(self):
        """EXT-07"""
        response = self._post(self.block(10, title='Cliente do WhatsApp'))

        self.assert_refused(response, '#/end_time', 'This field is required.')

    def test_an_end_time_not_after_the_start_is_refused(self):
        """EXT-08, with or without a service"""
        cases = (
            ('same time', local_iso(self.day, 10), {'title': 'Cliente do WhatsApp'}),
            ('a minute before', local_iso(self.day, 9, 59), {'title': 'Cliente do WhatsApp'}),
            ('same time with a service', local_iso(self.day, 10), {'service': self.service.id}),
        )
        for name, end_time, fields in cases:
            with self.subTest(name):
                response = self._post({'start_time': local_iso(self.day, 10), 'end_time': end_time, **fields})

                self.assert_refused(response, '#/end_time', 'The end time must be after the start time.')

    def test_a_start_time_in_the_past_is_refused(self):
        """EXT-09"""
        start = timezone.now() - timedelta(minutes=1)

        response = self._post({
            'start_time': start.isoformat(), 'end_time': (start + timedelta(hours=1)).isoformat(),
            'title': 'Cliente do WhatsApp',
        })

        self.assert_refused(response, '#/start_time', 'The start time must not be in the past.')

    def test_a_start_time_a_minute_ahead_is_accepted(self):
        """EXT-09"""
        start = timezone.now() + timedelta(minutes=1)

        response = self._post({
            'start_time': start.isoformat(), 'end_time': (start + timedelta(hours=1)).isoformat(),
            'title': 'Cliente do WhatsApp',
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Agenda.objects.count(), 2)

    def test_a_start_time_equal_to_now_is_accepted(self):
        """EXT-09: only a start before now is in the past (Assumptions: a start equal to now is accepted)"""
        frozen_now = manaus_in_utc(self.day, 10)

        with mock.patch('agenda.views.timezone.now', return_value=frozen_now):
            response = self._post(self.block(10, 11, title='Cliente do WhatsApp'))

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Agenda.objects.count(), 2)
        self.assertEqual(Agenda.objects.exclude(id=self.agenda.id).get().start_time, frozen_now)

    def test_a_block_without_a_service_that_crosses_another_block_answers_409(self):
        """EXT-10: the fixture block has a service"""
        start = self.agenda_start_time + timedelta(minutes=30)

        response = self._post({
            'start_time': start.isoformat(), 'end_time': (start + timedelta(hours=1)).isoformat(),
            'title': 'Cliente do WhatsApp',
        })

        assert_problem(response, 'agenda-overlap', detail='This time slot overlaps with an existing appointment.')
        self.assertEqual(Agenda.objects.count(), 1)

    def test_a_block_with_a_service_that_crosses_an_external_block_answers_409(self):
        """EXT-10: the existing block has no service"""
        Agenda.objects.create(
            start_time=manaus_in_utc(self.day, 15), end_time=manaus_in_utc(self.day, 16),
            hairdresser=self.hairdresser, service=None, title='Cliente do WhatsApp',
        )

        response = self._post({'start_time': local_iso(self.day, 15, 30), 'service': self.service.id})

        assert_problem(response, 'agenda-overlap', detail='This time slot overlaps with an existing appointment.')
        self.assertEqual(Agenda.objects.count(), 2)

    def test_a_block_that_starts_when_another_ends_is_accepted(self):
        """EXT-10"""
        response = self._post({
            'start_time': self.agenda_end_time.isoformat(),
            'end_time': (self.agenda_end_time + timedelta(hours=1)).isoformat(),
            'title': 'Cliente do WhatsApp',
        })

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Agenda.objects.count(), 2)

    def test_a_block_is_accepted_outside_the_availability(self):
        """EXT-13: on a day without Availability, after its closing time and in its break"""
        Availability.objects.create(
            hairdresser=self.hairdresser, weekday=calendar.day_name[self.day.weekday()].lower(),
            start_time=time(9, 0), end_time=time(17, 0), break_start=time(12, 0), break_end=time(13, 0),
        )
        cases = (
            ('day without availability', self.day + timedelta(days=1), (10, 0), (11, 0)),
            ('after closing time', self.day, (20, 0), (21, 0)),
            ('in the break', self.day, (12, 0), (12, 30)),
        )
        for name, day, start, end in cases:
            with self.subTest(name):
                response = self._post({
                    'start_time': local_iso(day, *start), 'end_time': local_iso(day, *end),
                    'title': 'Cliente do WhatsApp',
                })

                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                created = Agenda.objects.get(start_time=manaus_in_utc(day, *start))
                self.assertIsNone(created.service_id)


class ListAgendaTest(AgendaTestCase):
    def setUp(self):
        super().setUp()
        # An agenda of a different hairdresser, which must never show up below
        self.other_agenda = Agenda.objects.create(
            start_time=self.agenda_start_time,
            end_time=self.agenda_end_time,
            hairdresser=self.hairdresser2,
            service=self.service
        )

    def test_list_without_id_returns_only_the_session_hairdresser_agenda(self):
        """`list` no longer lists every agenda"""
        self.login(self.hairdresser_user)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([a['id'] for a in response.json()['data']], [self.agenda.id])

    def test_list_hairdresser_agendas(self):
        """Test listing agendas for a specific hairdresser"""
        self.login(self.hairdresser_user)
        list_hairdresser_url = reverse('hairdresser_agenda', args=[self.hairdresser.id])

        response = self.client.get(list_hairdresser_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([a['id'] for a in response.json()['data']], [self.agenda.id])

    def test_list_agenda_of_another_hairdresser_is_refused_with_403(self):
        self.login(self.hairdresser_user2)

        for hairdresser_id in (self.hairdresser.id, 9999):
            with self.subTest(hairdresser_id=hairdresser_id):
                response = self.client.get(reverse('hairdresser_agenda', args=[hairdresser_id]))
                assert_problem(response, 'forbidden')
                self.assertNotIn('data', response.json())

    def test_list_agenda_without_session_is_refused_with_401(self):
        for url in (self.list_url, reverse('hairdresser_agenda', args=[self.hairdresser.id])):
            with self.subTest(url=url):
                response = self.client.get(url)
                assert_problem(response, 'invalid-session')

    # External blocks (EXT-18, EXT-19)

    ITEM_KEYS = {'id', 'start_time', 'end_time', 'title', 'service', 'customer', 'reservation_id', 'customer_rating'}

    def create_external_block(self):
        start = self.agenda_start_time + timedelta(hours=3)
        return Agenda.objects.create(
            start_time=start, end_time=start + timedelta(hours=1),
            hairdresser=self.hairdresser, service=None, title='Cliente do WhatsApp',
        )

    def create_customer(self):
        user = User.objects.create(
            email='customer@example.com', first_name='Maria', last_name='Silva', phone='+5592984509999',
            neighborhood='X', city='Manaus', state='AM', address='Street', postal_code='69050750',
            role='customer', cognito_sub='sub-customer-1',
        )
        return Customer.objects.create(user=user, cpf='12345678901')

    def listed_items(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return {item['id']: item for item in response.json()['data']}

    def test_list_shows_an_external_block_with_its_title_and_no_service_or_customer(self):
        """EXT-18, on both list routes"""
        block = self.create_external_block()
        self.login(self.hairdresser_user)

        for url in (self.list_url, reverse('hairdresser_agenda', args=[self.hairdresser.id])):
            with self.subTest(url=url):
                items = self.listed_items(url)

                self.assertEqual(set(items), {self.agenda.id, block.id})
                for item in items.values():
                    self.assertEqual(set(item), self.ITEM_KEYS)
                self.assertIsNone(items[block.id]['service'])
                self.assertIsNone(items[block.id]['customer'])
                self.assertIsNone(items[block.id]['reservation_id'])
                self.assertIsNone(items[block.id]['customer_rating'])
                self.assertEqual(items[block.id]['title'], 'Cliente do WhatsApp')
                self.assertEqual(items[self.agenda.id]['service'], {'id': self.service.id, 'name': 'Haircut'})
                self.assertEqual(items[self.agenda.id]['title'], '')

    def test_a_reserve_at_the_start_of_an_external_block_is_not_its_customer(self):
        """EXT-19: a block without a service never pairs with a reserve"""
        block = self.create_external_block()
        Reserve.objects.create(start_time=block.start_time, customer=self.create_customer(), service=self.service)
        self.login(self.hairdresser_user)

        items = self.listed_items(self.list_url)

        self.assertIsNone(items[block.id]['customer'])

    def test_a_block_with_a_service_still_shows_the_customer_of_its_reserve(self):
        """EXT-19 regression: the reserve of a block with a service keeps naming its customer"""
        self.create_external_block()
        customer = self.create_customer()
        Reserve.objects.create(start_time=self.agenda_start_time, customer=customer, service=self.service)
        self.login(self.hairdresser_user)

        items = self.listed_items(self.list_url)

        self.assertEqual(
            items[self.agenda.id]['customer'],
            {
                'id': customer.id,
                'user': {'first_name': 'Maria', 'last_name': 'Silva', 'rating': customer.user.rating},
                'ratings_count': 0,
            },
        )

class RemoveAgendaTest(AgendaTestCase):
    def test_remove_agenda_success(self):
        """Test successful agenda removal"""
        self.login(self.hairdresser_user)
        response = self.client.delete(self.remove_url(self.agenda.id))
        
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.content, b'')
        self.assertEqual(Agenda.objects.count(), 0)
        
    def test_remove_nonexistent_agenda(self):
        """Test removing a non-existent agenda"""
        self.login(self.hairdresser_user)
        response = self.client.delete(self.remove_url(9999))  # Non-existent ID
        assert_problem(response, 'not-found', detail='Agenda slot not found.')

    def test_remove_agenda_of_another_hairdresser_is_refused_with_403(self):
        self.login(self.hairdresser_user2)

        response = self.client.delete(self.remove_url(self.agenda.id))

        assert_problem(response, 'forbidden')
        self.assertTrue(Agenda.objects.filter(id=self.agenda.id).exists())

    def test_remove_agenda_without_session_is_refused_with_401(self):
        response = self.client.delete(self.remove_url(self.agenda.id))

        assert_problem(response, 'invalid-session')
        self.assertTrue(Agenda.objects.filter(id=self.agenda.id).exists())


class AgendaCustomerRatingTest(AgendaTestCase):
    """CRT-36 to CRT-38: each agenda item names its reservation, the customer's rating and this reservation's rating."""

    def setUp(self):
        super().setUp()
        self.login(self.hairdresser_user)
        self.created = 0

    def _booked(self, rated=True, comment='Pontual'):
        """A past agenda slot with its reservation, for a new customer; rated 4 unless `rated` is False."""
        self.created += 1
        user = User.objects.create(
            email=f'customer{self.created}@example.com', first_name='Cliente', last_name=str(self.created),
            phone=f'55929000001{self.created:02d}', neighborhood='Centro', city='Manaus', state='AM',
            address='Rua A', postal_code='69000000', role='customer', rating=None,
        )
        customer = Customer.objects.create(user=user, cpf='12345678900')
        start = (timezone.now() - timedelta(days=self.created)).replace(microsecond=0)
        Agenda.objects.create(
            start_time=start, end_time=start + timedelta(minutes=60), hairdresser=self.hairdresser,
            service=self.service,
        )
        reserve = Reserve.objects.create(customer=customer, service=self.service, start_time=start)
        if rated:
            record_customer_rating(self.hairdresser, reserve, 4, comment)
        return reserve

    def _items(self, url):
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.json()['data']

    def test_a_booked_item_has_the_reservation_the_customer_rating_and_this_rating(self):
        """CRT-36, REV-55: the rating carries its id, which the app needs to edit and delete it."""
        rated = self._booked()
        unrated = self._booked(rated=False)
        urls = (self.list_url, reverse('hairdresser_agenda', args=[self.hairdresser.id]))
        for url in urls:
            with self.subTest(url=url):
                items = {item['reservation_id']: item for item in self._items(url)}

                self.assertEqual(items[rated.id]['customer'], {
                    'id': rated.customer_id,
                    'user': {'first_name': 'Cliente', 'last_name': '1', 'rating': 4.0},
                    'ratings_count': 1,
                })
                self.assertEqual(
                    items[rated.id]['customer_rating'],
                    {'id': rated.customer_rating.id, 'rating': 4, 'comment': 'Pontual'},
                )
                self.assertEqual(items[unrated.id]['customer'], {
                    'id': unrated.customer_id,
                    'user': {'first_name': 'Cliente', 'last_name': '2', 'rating': None},
                    'ratings_count': 0,
                })
                self.assertIsNone(items[unrated.id]['customer_rating'])

    def test_an_item_without_a_reservation_has_null_reservation_customer_and_rating(self):
        """CRT-37"""
        self._booked()

        item = next(item for item in self._items(self.list_url) if item['id'] == self.agenda.id)

        self.assertEqual(
            (item['reservation_id'], item['customer'], item['customer_rating']), (None, None, None),
        )

    def test_the_number_of_queries_does_not_grow_with_the_reservations(self):
        """CRT-38"""
        self._booked()
        with CaptureQueriesContext(connection) as one:
            self.assertEqual(len(self._items(self.list_url)), 2)
        for _ in range(4):
            self._booked()

        with self.assertNumQueries(len(one.captured_queries)):
            self.assertEqual(len(self._items(self.list_url)), 6)
