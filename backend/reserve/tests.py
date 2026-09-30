from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
import json
from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from django.utils import timezone

from users.models import User, Customer, Hairdresser
from service.models import Service
from reserve.models import Reserve
from agenda.models import Agenda
from availability.models import Availability
from users.cognito import get_cognito
from hairmatch.local_time import make_local_aware


class ReserveTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # URLs
        self.create_url = reverse('create_reserve')
        self.list_url = reverse('list_reserve')
        self.remove_url = lambda reserve_id: reverse('remove_reserve', args=[reserve_id])
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
        
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertEqual(response.json()['error'], 'The hairdresser is not available during this time slot.')
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

    def test_create_reserve_without_session_is_refused_with_401(self):
        self.logout()
        reserve_data = {
            'start_time': (self.reserve_start_time + timedelta(hours=2)).isoformat(),
            'customer': self.customer.id,
            'hairdresser': self.hairdresser.id,
            'service': self.service.id
        }

        response = self.client.post(self.create_url, data=json.dumps(reserve_data), content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
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

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(Reserve.objects.count(), 1)

    def test_create_reserve_with_a_service_of_another_hairdresser_is_refused(self):
        """The agenda block must land on the hairdresser who owns the service"""
        reserve_data = {
            'start_time': (self.reserve_start_time + timedelta(hours=2)).isoformat(),
            'hairdresser': self.hairdresser.id,
            'service': self.other_service.id
        }

        response = self.client.post(self.create_url, data=json.dumps(reserve_data), content_type='application/json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
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
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['error'], 'Hairdresser not found')
        
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
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['error'], 'Service not found')


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
        list_user_url = reverse('list_reserve', args=[self.customer.id])

        response = self.client.get(list_user_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([r['id'] for r in response.json()['data']], [self.reserve.id])

    def test_list_reserves_of_another_customer_is_refused_with_403(self):
        self.login(self.other_customer_user)

        response = self.client.get(reverse('list_reserve', args=[self.customer.id]))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertNotIn('data', response.json())

    def test_list_without_session_is_refused_with_401(self):
        for url in (self.list_url, reverse('list_reserve', args=[self.customer.id])):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ReserveByIdTest(ReserveTestCase):
    def url(self, reserve_id):
        return reverse('retrieve_reserve_by_id', args=[reserve_id])

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
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
                self.assertNotIn('data', response.json())

    def test_without_session_is_refused_with_401(self):
        response = self.client.get(self.url(self.reserve.id))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class RemoveReserveTest(ReserveTestCase):
    def test_remove_reserve_success(self):
        """Test successful reserve removal"""
        self.login(self.customer_user)
        response = self.client.delete(self.remove_url(self.reserve.id))
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['data'], 'reserve deleted successfully')
        self.assertEqual(Reserve.objects.count(), 0)
        
    def test_hairdresser_of_the_service_removes_the_reserve(self):
        self.login(self.hairdresser_user)

        response = self.client.delete(self.remove_url(self.reserve.id))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Reserve.objects.exists())

    def test_remove_nonexistent_reserve(self):
        """Test removing a non-existent reserve"""
        self.login(self.customer_user)
        response = self.client.delete(self.remove_url(9999))  # Non-existent ID
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_remove_reserve_of_someone_else_is_refused_with_403(self):
        for user in (self.other_customer_user, self.other_hairdresser_user):
            with self.subTest(user=user.email):
                self.login(user)
                response = self.client.delete(self.remove_url(self.reserve.id))
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
                self.assertTrue(Reserve.objects.filter(id=self.reserve.id).exists())

    def test_remove_without_session_is_refused_with_401(self):
        response = self.client.delete(self.remove_url(self.reserve.id))

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertTrue(Reserve.objects.filter(id=self.reserve.id).exists())


class ReserveSlotTest(ReserveTestCase):
    def test_get_available_slots(self):
        """Test getting available time slots for a hairdresser"""
        # Get tomorrow's date which is a Monday (to match our test availability)
        today = timezone.now().date()
        days_ahead = 7 - today.weekday()  # Next Monday
        next_monday = today + timedelta(days=days_ahead)
        
        slot_data = {
            'date': next_monday.strftime('%Y-%m-%d'),
            'service': self.service.id
        }
        
        response = self.client.post(
            self.get_slots_url(self.hairdresser.id),
            data=json.dumps(slot_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('available_slots', response.json())
        # The number of slots depends on service duration and availability
        # For a 60-minute service, 9am-5pm with 1hr lunch break,
        # we expect approximately 14 half-hour slots
        # This might need adjustment based on exact business logic
        
    def test_get_slots_invalid_hairdresser(self):
        """Test getting slots for non-existent hairdresser"""
        today = timezone.now().date()
        
        slot_data = {
            'date': today.strftime('%Y-%m-%d'),
            'service': self.service.id
        }
        
        response = self.client.post(
            self.get_slots_url(9999),  # Non-existent ID
            data=json.dumps(slot_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['error'], 'Hairdresser not found')
        
    def test_get_slots_invalid_service(self):
        """Test getting slots with non-existent service"""
        today = timezone.now().date()
        
        slot_data = {
            'date': today.strftime('%Y-%m-%d'),
            'service': 9999  # Non-existent ID
        }
        
        response = self.client.post(
            self.get_slots_url(self.hairdresser.id),
            data=json.dumps(slot_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['error'], 'Service not found')
        
    def test_get_slots_invalid_date_format(self):
        """Test getting slots with invalid date format"""
        slot_data = {
            'date': 'invalid-date',
            'service': self.service.id
        }
        
        response = self.client.post(
            self.get_slots_url(self.hairdresser.id),
            data=json.dumps(slot_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()['error'], 'Invalid date format. Please use YYYY-MM-DD.')
        
    def test_get_slots_no_availability(self):
        """Test getting slots when hairdresser has no availability for that day"""
        # Create a date for Tuesday, when we have no availability set
        today = timezone.now().date()
        days_ahead = (1 - today.weekday()) % 7 + 1  # Next Tuesday
        next_tuesday = today + timedelta(days=days_ahead)
        
        slot_data = {
            'date': next_tuesday.strftime('%Y-%m-%d'),
            'service': self.service.id
        }
        
        response = self.client.post(
            self.get_slots_url(self.hairdresser.id),
            data=json.dumps(slot_data),
            content_type='application/json'
        )
        
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
        response = self.client.post(
            self.get_slots_url(hairdresser.id),
            data=json.dumps({'date': day.isoformat(), 'service': service.id}),
            content_type='application/json'
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
