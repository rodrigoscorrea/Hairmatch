from django.test import TestCase, Client
from users.models import User, Customer, Hairdresser
from .models import Review
from django.urls import reverse
import json
import jwt
from datetime import datetime, timedelta


class ReviewTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Cria um cabeleireiro
        self.hairdresser_user = User.objects.create_user(
            email='hair@example.com',
            password='123456',
            phone='111111111',
            first_name='Hair',
            last_name='Dresser',
            street='Rua B',
            postal_code='00000-000',
            role='hairdresser'
        )
        self.hairdresser = Hairdresser.objects.create(user=self.hairdresser_user, cnpj='12345678000199')

        # Cria um cliente
        self.customer_user = User.objects.create_user(
            email='customer@example.com',
            password='123456',
            phone='999999999',
            first_name='Cust',
            last_name='Omer',
            street='Rua A',
            postal_code='11111-111',
            role='customer'
        )
        self.customer = Customer.objects.create(user=self.customer_user, cpf='12345678900')

        # Gera token de autenticação
        self.token = jwt.encode({
            'id': self.customer_user.id,
            'exp': datetime.utcnow() + timedelta(hours=1)
        }, 'secret', algorithm='HS256')

        self.cookies = {'jwt': self.token}

    def test_create_review(self):
        data = {
            'rating': 4.5,
            'comment': 'Muito bom!',
            'hairdresser': self.hairdresser.id
        }
        response = self.client.post(
            reverse('create_review'),
            data=json.dumps(data),
            content_type='application/json',
            **{'HTTP_COOKIE': f'jwt={self.token}'}
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Review.objects.count(), 1)

    def test_list_review(self):
        Review.objects.create(
            rating=5,
            comment="Ótimo serviço",
            customer=self.customer,
            hairdresser=self.hairdresser
        )
        response = self.client.get(reverse('list_review', args=[self.hairdresser.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json().get('data')), 1)

    def test_update_review(self):
        review = Review.objects.create(
            rating=3,
            comment="Regular",
            customer=self.customer,
            hairdresser=self.hairdresser
        )
        data = {
            'rating': 4,
            'comment': "Melhorou!"
        }
        response = self.client.put(
            reverse('update_review', args=[review.id]),
            data=json.dumps(data),
            content_type='application/json',
            **{'HTTP_COOKIE': f'jwt={self.token}'}
        )
        self.assertEqual(response.status_code, 200)
        review.refresh_from_db()
        self.assertEqual(review.rating, 4)
        self.assertEqual(review.comment, "Melhorou!")

    def test_delete_review(self):
        review = Review.objects.create(
            rating=3,
            comment="Regular",
            customer=self.customer,
            hairdresser=self.hairdresser
        )
        response = self.client.delete(
            reverse('remove_review', args=[review.id]),
            **{'HTTP_COOKIE': f'jwt={self.token}'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Review.objects.count(), 0)

    def test_delete_review_admin(self):
        review = Review.objects.create(
            rating=2,
            comment="Ruim",
            customer=self.customer,
            hairdresser=self.hairdresser
        )
        response = self.client.delete(reverse('remove_review'), args=[review.id])
        self.assertEqual(response.status_code, 404)  # rota errada propositalmente

        # Correto
        response = self.client.delete(reverse('remove_review', args=[review.id]))
        self.assertEqual(response.status_code, 403)  # não é admin, logo bloqueia

        # Vamos testar rota admin correta
        response = self.client.delete(reverse('remove_review_admin', args=[review.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Review.objects.count(), 0)
