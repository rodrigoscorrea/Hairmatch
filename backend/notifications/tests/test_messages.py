import datetime
from zoneinfo import ZoneInfo

from django.test import SimpleTestCase

from notifications import messages
from notifications.models import Alert
from review.models import CustomerRating, Review
from reserve.models import Reserve
from service.models import Service
from users.models import Customer, Hairdresser, User

UTC = datetime.timezone.utc


def build_user(first_name, last_name, role):
    return User(first_name=first_name, last_name=last_name, role=role, email=f'{first_name}@example.com')


class Scenario(SimpleTestCase):
    """Unsaved rows are enough: the messages only read fields and relations."""

    def setUp(self):
        self.customer_user = build_user('Ana', 'Souza', 'customer')
        self.hairdresser_user = build_user('Bruno', 'Lima', 'hairdresser')
        self.customer = Customer(pk=1, user=self.customer_user)
        self.hairdresser = Hairdresser(pk=2, user=self.hairdresser_user)
        self.service = Service(pk=3, name='Corte feminino', hairdresser=self.hairdresser)

    def reserve(self, start_time):
        return Reserve(pk=11, start_time=start_time, customer=self.customer, service=self.service)

    def review(self, rating):
        return Review(pk=12, rating=rating, customer=self.customer, hairdresser=self.hairdresser)

    def customer_rating(self, rating):
        return CustomerRating(pk=13, rating=rating, customer=self.customer, hairdresser=self.hairdresser)


class CatalogTextTest(Scenario):
    def test_reservation_created(self):
        """NOTIF-28, NOTIF-27"""
        message = messages.reservation_created(self.reserve(datetime.datetime(2026, 10, 20, 13, 0, tzinfo=UTC)))

        self.assertEqual(
            (message.recipient, message.kind, message.title, message.body, message.data),
            (
                self.hairdresser_user, 'reservation-created', 'Nova reserva',
                'Ana Souza reservou Corte feminino para 20/10 às 09:00.', {'reservation_id': 11},
            ),
        )

    def test_review_created(self):
        """NOTIF-32"""
        message = messages.review_created(self.review(4.5))

        self.assertEqual(
            (message.recipient, message.kind, message.title, message.body, message.data),
            (
                self.hairdresser_user, 'review-created', 'Nova avaliação',
                'Ana Souza avaliou seu atendimento com 4,5 estrelas.', {'review_id': 12},
            ),
        )

    def test_review_updated(self):
        """NOTIF-59"""
        message = messages.review_updated(self.review(5.0))

        self.assertEqual(
            (message.recipient, message.kind, message.title, message.body, message.data),
            (
                self.hairdresser_user, 'review-updated', 'Avaliação atualizada',
                'Ana Souza atualizou a avaliação do seu atendimento: 5 estrelas.', {'review_id': 12},
            ),
        )

    def test_review_deleted(self):
        """NOTIF-60"""
        message = messages.review_deleted(self.review(3.0))

        self.assertEqual(
            (message.recipient, message.kind, message.title, message.body, message.data),
            (
                self.hairdresser_user, 'review-deleted', 'Avaliação removida',
                'Ana Souza removeu a avaliação do seu atendimento.', {},
            ),
        )

    def test_customer_rating_created(self):
        """NOTIF-35"""
        message = messages.customer_rating_created(self.customer_rating(5))

        self.assertEqual(
            (message.recipient, message.kind, message.title, message.body, message.data),
            (
                self.customer_user, 'customer-rating-created', 'Você foi avaliado',
                'Bruno Lima deu nota 5 para você.', {'customer_rating_id': 13},
            ),
        )

    def test_customer_rating_updated(self):
        """NOTIF-64"""
        message = messages.customer_rating_updated(self.customer_rating(2))

        self.assertEqual(
            (message.recipient, message.kind, message.title, message.body, message.data),
            (
                self.customer_user, 'customer-rating-updated', 'Avaliação atualizada',
                'Bruno Lima mudou sua nota para 2.', {'customer_rating_id': 13},
            ),
        )

    def test_customer_rating_deleted(self):
        """NOTIF-65"""
        message = messages.customer_rating_deleted(self.customer_rating(2))

        self.assertEqual(
            (message.recipient, message.kind, message.title, message.body, message.data),
            (
                self.customer_user, 'customer-rating-deleted', 'Avaliação removida',
                'Bruno Lima removeu a nota que deu a você.', {},
            ),
        )

    def test_every_kind_of_the_catalog_is_a_kind_of_the_alert_model(self):
        """NOTIF-19: a message that the Alert column refuses would undo the action."""
        built = [
            messages.reservation_created(self.reserve(datetime.datetime(2026, 10, 20, 13, 0, tzinfo=UTC))),
            messages.review_created(self.review(5.0)), messages.review_updated(self.review(5.0)),
            messages.review_deleted(self.review(5.0)),
            messages.customer_rating_created(self.customer_rating(5)),
            messages.customer_rating_updated(self.customer_rating(5)),
            messages.customer_rating_deleted(self.customer_rating(5)),
        ]

        self.assertEqual(sorted(message.kind for message in built), sorted(Alert.KINDS))

    def test_a_long_service_name_cannot_overflow_the_body_column(self):
        """NOTIF-20: the insert of a too long body would fail and undo the reservation."""
        self.service.name = 'S' * 200
        self.customer_user.first_name = 'A' * 100
        self.customer_user.last_name = 'B' * 100

        message = messages.reservation_created(self.reserve(datetime.datetime(2026, 10, 20, 13, 0, tzinfo=UTC)))

        self.assertEqual(len(message.body), 300)
        self.assertTrue(message.body.endswith('…'))


class ManausClockTest(Scenario):
    def test_13h_utc_is_9h_in_manaus(self):
        """NOTIF-27"""
        message = messages.reservation_created(self.reserve(datetime.datetime(2026, 10, 20, 13, 0, tzinfo=UTC)))

        self.assertIn('para 20/10 às 09:00.', message.body)

    def test_0330_utc_of_the_2nd_is_2330_of_the_1st_in_manaus(self):
        """NOTIF-27: the date moves back with the hour."""
        message = messages.reservation_created(self.reserve(datetime.datetime(2026, 11, 2, 3, 30, tzinfo=UTC)))

        self.assertIn('para 01/11 às 23:30.', message.body)

    def test_a_time_in_another_zone_is_converted_to_manaus(self):
        """NOTIF-27"""
        sao_paulo = datetime.datetime(2026, 10, 20, 10, 0, tzinfo=ZoneInfo('America/Sao_Paulo'))

        message = messages.reservation_created(self.reserve(sao_paulo))

        self.assertIn('às 09:00.', message.body)


class RatingFormatTest(Scenario):
    def test_a_whole_rating_has_no_decimal_and_a_half_one_has_a_comma(self):
        """NOTIF-32 (assumption: formato da nota)"""
        self.assertEqual(
            [messages.format_rating(value) for value in (5.0, 4.5, 1.0, 3)], ['5', '4,5', '1', '3'],
        )

    def test_one_star_is_singular_and_every_other_rating_is_plural(self):
        """NOTIF-32"""
        self.assertEqual(
            [messages.stars(value) for value in (1.0, 1.5, 2.0, 5.0)], ['estrela', 'estrelas', 'estrelas', 'estrelas'],
        )

    def test_the_review_body_uses_estrela_only_for_a_rating_of_1(self):
        """NOTIF-32"""
        self.assertEqual(
            messages.review_created(self.review(1.0)).body, 'Ana Souza avaliou seu atendimento com 1 estrela.',
        )
