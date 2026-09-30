from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
import json
from datetime import datetime, timedelta, timezone as dt_timezone
from django.utils import timezone

from users.models import User, Hairdresser
from service.models import Service
from agenda.models import Agenda
from users.cognito import get_cognito
from hairmatch.problem_testing import assert_problem


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


class CreateAgendaTest(AgendaTestCase):
    def setUp(self):
        super().setUp()
        self.login(self.hairdresser_user)

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
        response = self._post({})

        assert_problem(response, 'validation-error', errors=[
            {'pointer': '#/start_time', 'detail': 'This field is required.'},
            {'pointer': '#/service', 'detail': 'This field is required.'},
        ])

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
        list_hairdresser_url = reverse('list_agenda', args=[self.hairdresser.id])

        response = self.client.get(list_hairdresser_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([a['id'] for a in response.json()['data']], [self.agenda.id])

    def test_list_agenda_of_another_hairdresser_is_refused_with_403(self):
        self.login(self.hairdresser_user2)

        for hairdresser_id in (self.hairdresser.id, 9999):
            with self.subTest(hairdresser_id=hairdresser_id):
                response = self.client.get(reverse('list_agenda', args=[hairdresser_id]))
                assert_problem(response, 'forbidden')
                self.assertNotIn('data', response.json())

    def test_list_agenda_without_session_is_refused_with_401(self):
        for url in (self.list_url, reverse('list_agenda', args=[self.hairdresser.id])):
            with self.subTest(url=url):
                response = self.client.get(url)
                assert_problem(response, 'invalid-session')

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
