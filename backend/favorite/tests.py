import datetime

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from users.models import Customer, Hairdresser, User

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
