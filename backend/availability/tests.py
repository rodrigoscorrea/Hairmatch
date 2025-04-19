from django.test import TestCase, Client
from django.contrib.auth.models import User
from users.models import Hairdresser
from .models import Availability
import json
import jwt
import datetime


class AvailabilityTestCase(TestCase):
    def setUp(self):
        # Cliente de testes do Django
        self.client = Client()

        # Criando um usuário e associando a um Hairdresser
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.hairdresser = Hairdresser.objects.create(user=self.user)

        # Gerar token JWT válido
        self.token = self.get_token_for_user(self.user)

    def get_token_for_user(self, user):
        payload = {
            'id': user.id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1),
            'iat': datetime.datetime.utcnow()
        }
        return jwt.encode(payload, 'secret', algorithm='HS256')

    def test_create_availability_successfully(self):
        data = {
            'weekday': 'Segunda',
            'start_time': '09:00',
            'end_time': '17:00'
        }
        response = self.client.post(
            '/availability/create',
            json.dumps(data),
            content_type='application/json',
            cookies={'jwt': self.token}
        )
        self.assertEqual(response.status_code, 201)
        self.assertIn('Availability registered successfully', response.json().get('message'))

    def test_create_availability_missing_fields(self):
        data = {
            'weekday': 'Segunda'
        }
        response = self.client.post(
            '/availability/create',
            json.dumps(data),
            content_type='application/json',
            cookies={'jwt': self.token}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('One of the following required fields is missing', response.json().get('error'))

    def test_create_availability_invalid_token(self):
        data = {
            'weekday': 'Sexta',
            'start_time': '10:00',
            'end_time': '18:00'
        }
        response = self.client.post(
            '/availability/create',
            json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn('Invalid token', response.json().get('error'))

    def test_list_availabilities(self):
        Availability.objects.create(
            weekday='Quarta',
            start_time='08:00',
            end_time='12:00',
            hairdresser=self.hairdresser
        )
        response = self.client.get(f'/availability/list/{self.hairdresser.id}')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(isinstance(response.json().get('data'), list))
        self.assertEqual(len(response.json().get('data')), 1)

    def test_update_availability(self):
        availability = Availability.objects.create(
            weekday='Terça',
            start_time='10:00',
            end_time='18:00',
            hairdresser=self.hairdresser
        )
        data = {'end_time': '19:00'}
        response = self.client.put(
            f'/availability/update/{availability.id}',
            json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('message'), 'Availability updated successfully')

    def test_remove_availability(self):
        availability = Availability.objects.create(
            weekday='Quarta',
            start_time='08:00',
            end_time='12:00',
            hairdresser=self.hairdresser
        )
        response = self.client.delete(f'/availability/remove/{availability.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json().get('message'), 'Availability removed successfully')

    def test_remove_availability_not_found(self):
        response = self.client.delete(f'/availability/remove/9999')
        self.assertEqual(response.status_code, 404)
        self.assertIn('Availability not found', response.json().get('error'))

    def test_update_availability_not_found(self):
        data = {'end_time': '20:00'}
        response = self.client.put(
            f'/availability/update/9999',
            json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn('Availability not found', response.json().get('error'))
