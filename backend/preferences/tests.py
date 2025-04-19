from django.test import TestCase, Client
from users.models import User
from preferences.models import Preferences
from django.urls import reverse
import json
import jwt
from datetime import datetime, timedelta
from django.core.files.uploadedfile import SimpleUploadedFile


class PreferencesTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Usuário 1
        self.user1 = User.objects.create_user(
            email='user1@example.com',
            password='123456',
            phone='999999999',
            first_name='João',
            last_name='Silva',
            street='Rua A',
            postal_code='11111-111',
            role='customer'
        )

        # Usuário 2
        self.user2 = User.objects.create_user(
            email='user2@example.com',
            password='123456',
            phone='888888888',
            first_name='Maria',
            last_name='Souza',
            street='Rua B',
            postal_code='22222-222',
            role='customer'
        )

        self.token_user1 = jwt.encode({
            'id': self.user1.id,
            'exp': datetime.utcnow() + timedelta(hours=1)
        }, 'secret', algorithm='HS256')

        self.token_expired = jwt.encode({
            'id': self.user1.id,
            'exp': datetime.utcnow() - timedelta(seconds=1)
        }, 'secret', algorithm='HS256')

    def test_create_preference(self):
        data = {'name': 'Corte curto', 'picture': ''}
        response = self.client.post(
            reverse('create_preferences'),
            data=json.dumps(data),
            content_type='application/json',
            **{'HTTP_COOKIE': f'jwt={self.token_user1}'}
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Preferences.objects.count(), 1)

    def test_create_preference_with_image(self):
        image = SimpleUploadedFile("cut.png", b"imagecontent", content_type="image/png")
        pref = Preferences.objects.create(name='Com Imagem', picture=image)
        pref.user_id.set([self.user1])
        self.assertTrue(pref.picture.name.endswith('cut.png'))

    def test_create_preference_invalid_token(self):
        data = {'name': 'Barba'}
        response = self.client.post(
            reverse('create_preferences'),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn('Invalid token', response.json()['error'])

    def test_create_preference_expired_token(self):
        data = {'name': 'Barba'}
        response = self.client.post(
            reverse('create_preferences'),
            data=json.dumps(data),
            content_type='application/json',
            **{'HTTP_COOKIE': f'jwt={self.token_expired}'}
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn('Token expired', response.json()['error'])

    def test_create_preference_missing_fields(self):
        data = {}  # sem 'name'
        response = self.client.post(
            reverse('create_preferences'),
            data=json.dumps(data),
            content_type='application/json',
            **{'HTTP_COOKIE': f'jwt={self.token_user1}'}
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('name', response.json()['error'])

    def test_list_preferences_by_user(self):
        p1 = Preferences.objects.create(name='Corte 1', picture='')
        p1.user_id.set([self.user1])
        p2 = Preferences.objects.create(name='Corte 2', picture='')
        p2.user_id.set([self.user2])

        response_user1 = self.client.get(reverse('list_preferences', args=[self.user1.id]))
        response_user2 = self.client.get(reverse('list_preferences', args=[self.user2.id]))

        self.assertEqual(len(response_user1.json()), 1)
        self.assertEqual(response_user1.json()[0]['name'], 'Corte 1')

        self.assertEqual(len(response_user2.json()), 1)
        self.assertEqual(response_user2.json()[0]['name'], 'Corte 2')

    def test_update_preference(self):
        pref = Preferences.objects.create(name='Corte longo', picture='')
        pref.user_id.set([self.user1])
        data = {'name': 'Corte médio'}

        response = self.client.put(
            reverse('update_preferences', args=[pref.id]),
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        pref.refresh_from_db()
        self.assertEqual(pref.name, 'Corte médio')

    def test_update_nonexistent_preference(self):
        response = self.client.put(
            reverse('update_preferences', args=[999]),
            data=json.dumps({'name': 'Qualquer'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 404)

    def test_remove_preference(self):
        pref = Preferences.objects.create(name='Luzes', picture='')
        pref.user_id.set([self.user1])
        response = self.client.delete(reverse('remove_preferences', args=[pref.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Preferences.objects.count(), 0)

    def test_remove_nonexistent_preference(self):
        response = self.client.delete(reverse('remove_preferences', args=[999]))
        self.assertEqual(response.status_code, 404)
