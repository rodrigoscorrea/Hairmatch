import datetime
import json
import threading

from django.db import IntegrityError, connection, transaction
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from hairmatch.problem_testing import assert_problem
from users.models import Customer, Hairdresser, User
from users.testing import activate_account

from .models import FavoriteHairdresser


def make_user(email, phone, role):
    return User.objects.create(
        first_name='Fav', last_name=role, email=email, phone=phone, neighborhood='Centro', city='Manaus',
        state='AM', address='Rua A', postal_code='69000000', role=role,
    )


def make_customer(index):
    return Customer.objects.create(user=make_user(f'c{index}@example.com', f'55929000000{index}', 'customer'), cpf='1')


def make_hairdresser(index):
    return Hairdresser.objects.create(user=make_user(f'h{index}@example.com', f'55929000010{index}', 'hairdresser'), cnpj='1')


class FavoriteHairdresserModelTest(TestCase):
    def setUp(self):
        self.customer = make_customer(1)
        self.other_customer = make_customer(2)
        self.hairdressers = [make_hairdresser(index) for index in range(1, 4)]

    def test_the_same_pair_cannot_be_stored_twice(self):
        """FAV-03"""
        FavoriteHairdresser.objects.create(customer=self.customer, hairdresser=self.hairdressers[0])

        with self.assertRaises(IntegrityError), transaction.atomic():
            FavoriteHairdresser.objects.create(customer=self.customer, hairdresser=self.hairdressers[0])

        self.assertEqual(FavoriteHairdresser.objects.count(), 1)

    def test_the_same_hairdresser_can_be_favorited_by_two_customers(self):
        """FAV-03: the pair is unique, not the hairdresser."""
        FavoriteHairdresser.objects.create(customer=self.customer, hairdresser=self.hairdressers[0])
        FavoriteHairdresser.objects.create(customer=self.other_customer, hairdresser=self.hairdressers[0])

        self.assertEqual(FavoriteHairdresser.objects.count(), 2)

    def test_the_default_order_is_the_most_recently_favorited_first(self):
        """FAV-19: created_at is rewritten out of insertion order, so only Meta.ordering can produce this result."""
        now = timezone.now()
        favorites = [
            FavoriteHairdresser.objects.create(customer=self.customer, hairdresser=hairdresser)
            for hairdresser in self.hairdressers
        ]
        for favorite, age in zip(favorites, (datetime.timedelta(days=1), datetime.timedelta(days=3), datetime.timedelta(days=2))):
            FavoriteHairdresser.objects.filter(pk=favorite.pk).update(created_at=now - age)

        ordered = FavoriteHairdresser.objects.filter(customer=self.customer)

        self.assertEqual(
            [favorite.hairdresser_id for favorite in ordered],
            [self.hairdressers[0].id, self.hairdressers[2].id, self.hairdressers[1].id],
        )

    def test_a_tie_on_created_at_is_broken_by_the_id_descending(self):
        """FAV-19"""
        moment = timezone.now()
        favorites = [
            FavoriteHairdresser.objects.create(customer=self.customer, hairdresser=hairdresser)
            for hairdresser in self.hairdressers[:2]
        ]
        FavoriteHairdresser.objects.filter(customer=self.customer).update(created_at=moment)

        ordered = FavoriteHairdresser.objects.filter(customer=self.customer)

        self.assertEqual([favorite.id for favorite in ordered], [favorites[1].id, favorites[0].id])

    def test_deleting_a_customer_deletes_only_their_favorites(self):
        """FAV-36"""
        FavoriteHairdresser.objects.create(customer=self.customer, hairdresser=self.hairdressers[0])
        FavoriteHairdresser.objects.create(customer=self.customer, hairdresser=self.hairdressers[1])
        kept = FavoriteHairdresser.objects.create(customer=self.other_customer, hairdresser=self.hairdressers[0])

        self.customer.delete()

        self.assertEqual(list(FavoriteHairdresser.objects.all()), [kept])

    def test_deleting_a_hairdresser_deletes_the_favorites_of_every_customer(self):
        """FAV-37"""
        FavoriteHairdresser.objects.create(customer=self.customer, hairdresser=self.hairdressers[0])
        FavoriteHairdresser.objects.create(customer=self.other_customer, hairdresser=self.hairdressers[0])
        kept = FavoriteHairdresser.objects.create(customer=self.customer, hairdresser=self.hairdressers[1])

        self.hairdressers[0].delete()

        self.assertEqual(list(FavoriteHairdresser.objects.all()), [kept])


class FavoriteAccounts:
    """Accounts created the way a user does: POST /api/users, the e-mail confirmation and a login that keeps the cookies."""
    PASSWORD = 'Password123'

    def sign_up(self, role, index):
        """Returns (profile, logged-in APIClient) of a new active customer or hairdresser."""
        email = f'{role}{index}@example.com'
        payload = {
            'email': email, 'first_name': f'Fav{index}', 'last_name': role.capitalize(), 'password': self.PASSWORD,
            'phone': f'+559298450{index:04d}', 'complement': 'Apt 1', 'neighborhood': 'Centro', 'city': 'Manaus',
            'state': 'AM', 'address': 'Rua A', 'number': '12', 'postal_code': '69050750', 'role': role,
            'preferences': json.dumps([]),
        }
        if role == 'customer':
            payload['cpf'] = '12345678901'
        else:
            payload.update({
                'cnpj': '12345678901234', 'experience_years': 5, 'resume': 'Resume', 'experience_time': '5 anos',
                'experiences': 'Cortes', 'products': 'Produtos',
            })
        client = APIClient()
        response = client.post(reverse('register'), data=payload)
        assert response.status_code == 201, response.content
        activate_account(email)
        login = client.post(
            reverse('login'), data=json.dumps({'email': email, 'password': self.PASSWORD}), content_type='application/json',
        )
        assert login.status_code == 200, login.content
        user = User.objects.get(email=email)
        profile = Customer.objects.get(user=user) if role == 'customer' else Hairdresser.objects.get(user=user)
        return profile, client

    def detail_url(self, hairdresser_id):
        return f'/api/customers/me/favorite-hairdressers/{hairdresser_id}'

    def rows(self):
        return list(FavoriteHairdresser.objects.order_by('id').values_list('id', 'customer_id', 'hairdresser_id', 'created_at'))


class FavoriteHairdresserDetailTest(FavoriteAccounts, TestCase):
    """PUT and DELETE /api/customers/me/favorite-hairdressers/{id} (RT-98, RT-99)."""

    def setUp(self):
        self.customer_a, self.client_a = self.sign_up('customer', 1)
        self.customer_b, self.client_b = self.sign_up('customer', 2)
        self.hairdresser_1, self.hairdresser_client = self.sign_up('hairdresser', 3)
        self.hairdresser_2, _ = self.sign_up('hairdresser', 4)
        self.anonymous = APIClient()

    def test_put_favorites_an_active_hairdresser(self):
        """FAV-01"""
        response = self.client_a.put(self.detail_url(self.hairdresser_1.id))

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b'')
        favorite = FavoriteHairdresser.objects.get()
        self.assertEqual((favorite.customer_id, favorite.hairdresser_id), (self.customer_a.id, self.hairdresser_1.id))

    def test_a_repeated_put_answers_204_and_keeps_the_original_row(self):
        """FAV-02"""
        self.client_a.put(self.detail_url(self.hairdresser_1.id))
        before = self.rows()

        response = self.client_a.put(self.detail_url(self.hairdresser_1.id))

        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.rows(), before)
        self.assertEqual(len(before), 1)

    def test_put_for_a_hairdresser_that_does_not_exist_answers_404(self):
        """FAV-04"""
        response = self.client_a.put(self.detail_url(999999))

        assert_problem(response, 'not-found', 'Hairdresser not found.')
        self.assertEqual(FavoriteHairdresser.objects.count(), 0)

    def test_put_for_a_pending_hairdresser_answers_404(self):
        """FAV-05"""
        User.objects.filter(pk=self.hairdresser_1.user_id).update(is_active=False)

        response = self.client_a.put(self.detail_url(self.hairdresser_1.id))

        assert_problem(response, 'not-found', 'Hairdresser not found.')
        self.assertEqual(FavoriteHairdresser.objects.count(), 0)

    def test_delete_removes_only_the_pair(self):
        """FAV-06"""
        self.client_a.put(self.detail_url(self.hairdresser_1.id))
        self.client_a.put(self.detail_url(self.hairdresser_2.id))

        response = self.client_a.delete(self.detail_url(self.hairdresser_1.id))

        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.content, b'')
        remaining = FavoriteHairdresser.objects.get()
        self.assertEqual((remaining.customer_id, remaining.hairdresser_id), (self.customer_a.id, self.hairdresser_2.id))

    def test_delete_of_a_hairdresser_that_is_not_a_favorite_answers_204(self):
        """FAV-07"""
        self.client_a.put(self.detail_url(self.hairdresser_2.id))
        before = self.rows()

        response = self.client_a.delete(self.detail_url(self.hairdresser_1.id))

        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.rows(), before)

    def test_delete_of_a_pending_hairdresser_answers_204_and_removes_the_favorite(self):
        """Assumption: DELETE answers 204 for any hairdresser that exists, so a favorite that turned pending can go."""
        self.client_a.put(self.detail_url(self.hairdresser_1.id))
        User.objects.filter(pk=self.hairdresser_1.user_id).update(is_active=False)

        response = self.client_a.delete(self.detail_url(self.hairdresser_1.id))

        self.assertEqual(response.status_code, 204)
        self.assertEqual(FavoriteHairdresser.objects.count(), 0)

    def test_delete_for_a_hairdresser_that_does_not_exist_answers_404(self):
        """FAV-08"""
        self.client_a.put(self.detail_url(self.hairdresser_1.id))
        before = self.rows()

        response = self.client_a.delete(self.detail_url(999999))

        assert_problem(response, 'not-found', 'Hairdresser not found.')
        self.assertEqual(self.rows(), before)

    def test_without_a_session_put_and_delete_answer_401_and_change_nothing(self):
        """FAV-09"""
        self.client_a.put(self.detail_url(self.hairdresser_1.id))
        before = self.rows()

        for method in (self.anonymous.put, self.anonymous.delete):
            with self.subTest(method=method.__name__):
                assert_problem(method(self.detail_url(self.hairdresser_1.id)), 'invalid-session')
                assert_problem(method(self.detail_url(self.hairdresser_2.id)), 'invalid-session')

        self.assertEqual(self.rows(), before)

    def test_with_a_hairdresser_session_put_and_delete_answer_403_and_change_nothing(self):
        """FAV-10"""
        self.client_a.put(self.detail_url(self.hairdresser_1.id))
        before = self.rows()

        for method in (self.hairdresser_client.put, self.hairdresser_client.delete):
            with self.subTest(method=method.__name__):
                assert_problem(method(self.detail_url(self.hairdresser_1.id)), 'customer-required')
                assert_problem(method(self.detail_url(self.hairdresser_2.id)), 'customer-required')

        self.assertEqual(self.rows(), before)

    def test_a_customer_unfavoriting_keeps_the_favorites_of_other_customers(self):
        """FAV-11"""
        self.client_a.put(self.detail_url(self.hairdresser_1.id))
        self.client_b.put(self.detail_url(self.hairdresser_1.id))

        self.client_a.delete(self.detail_url(self.hairdresser_1.id))

        remaining = FavoriteHairdresser.objects.get()
        self.assertEqual((remaining.customer_id, remaining.hairdresser_id), (self.customer_b.id, self.hairdresser_1.id))

    def test_a_path_id_that_is_not_an_integer_answers_404(self):
        """FAV-39"""
        for method in (self.client_a.put, self.client_a.delete):
            with self.subTest(method=method.__name__):
                assert_problem(method('/api/customers/me/favorite-hairdressers/abc'), 'not-found')

        self.assertEqual(FavoriteHairdresser.objects.count(), 0)


class FavoriteHairdresserRaceTest(FavoriteAccounts, TransactionTestCase):
    """FAV-03: simultaneous PUTs of the same pair answer 204 and leave one row."""

    ROUNDS = 5
    REQUESTS_PER_ROUND = 4

    def test_simultaneous_puts_of_the_same_pair_leave_one_row(self):
        customer, client = self.sign_up('customer', 1)
        hairdresser, _ = self.sign_up('hairdresser', 2)
        url = self.detail_url(hairdresser.id)

        for round_number in range(self.ROUNDS):
            FavoriteHairdresser.objects.all().delete()
            barrier = threading.Barrier(self.REQUESTS_PER_ROUND)
            statuses = []
            failures = []

            def put():
                try:
                    barrier.wait(timeout=10)
                    statuses.append(client.put(url).status_code)
                except Exception as exc:  # reported below: an exception in a thread does not fail the test
                    failures.append(exc)
                finally:
                    connection.close()

            threads = [threading.Thread(target=put) for _ in range(self.REQUESTS_PER_ROUND)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(timeout=30)

            with self.subTest(round=round_number):
                self.assertEqual(failures, [])
                self.assertEqual(statuses, [204] * self.REQUESTS_PER_ROUND)
                self.assertEqual(FavoriteHairdresser.objects.filter(customer=customer, hairdresser=hairdresser).count(), 1)
