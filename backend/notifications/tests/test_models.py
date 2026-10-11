import datetime

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from notifications.models import Alert, PushDevice

from .helpers import make_user


def make_alert(recipient, **extra):
    return Alert.objects.create(
        recipient=recipient, kind='reservation-created', title='Nova reserva', body='Ana reservou Corte.', **extra,
    )


class PushDeviceModelTest(TestCase):
    def setUp(self):
        self.user = make_user('a@example.com', '5592900000001')
        self.other = make_user('b@example.com', '5592900000002')

    def test_the_token_is_unique_in_the_system(self):
        """NOTIF-04: a second row with the same token is refused, whichever the account."""
        PushDevice.objects.create(user=self.user, token='token-1', endpoint_arn='arn:1')

        with self.assertRaises(IntegrityError), transaction.atomic():
            PushDevice.objects.create(user=self.other, token='token-1', endpoint_arn='arn:2')

        self.assertEqual(PushDevice.objects.filter(token='token-1').count(), 1)

    def test_deleting_the_user_deletes_only_their_devices(self):
        """NOTIF-11"""
        PushDevice.objects.create(user=self.user, token='token-1', endpoint_arn='arn:1')
        PushDevice.objects.create(user=self.user, token='token-2', endpoint_arn='arn:2')
        kept = PushDevice.objects.create(user=self.other, token='token-3', endpoint_arn='arn:3')

        self.user.delete()

        self.assertEqual(list(PushDevice.objects.all()), [kept])


class AlertModelTest(TestCase):
    def setUp(self):
        self.user = make_user('a@example.com', '5592900000001')
        self.other = make_user('b@example.com', '5592900000002')

    def test_a_new_alert_is_unread(self):
        alert = make_alert(self.user)

        self.assertIsNone(alert.read_at)

    def test_the_default_order_is_the_newest_first_whatever_the_insertion_order(self):
        """NOTIF-39: an old alert inserted after a new one still comes last."""
        now = timezone.now()
        newer = make_alert(self.user)
        older = make_alert(self.user)
        Alert.objects.filter(pk=newer.pk).update(created_at=now)
        Alert.objects.filter(pk=older.pk).update(created_at=now - datetime.timedelta(days=1))

        self.assertEqual([alert.pk for alert in Alert.objects.all()], [newer.pk, older.pk])

    def test_a_tie_on_created_at_is_broken_by_the_larger_id_first(self):
        """NOTIF-39"""
        moment = timezone.now()
        first = make_alert(self.user)
        second = make_alert(self.user)
        Alert.objects.update(created_at=moment)

        self.assertEqual([alert.pk for alert in Alert.objects.all()], [second.pk, first.pk])

    def test_deleting_the_user_deletes_only_their_alerts(self):
        """NOTIF-46"""
        make_alert(self.user)
        make_alert(self.user)
        kept = make_alert(self.other)

        self.user.delete()

        self.assertEqual(list(Alert.objects.all()), [kept])
