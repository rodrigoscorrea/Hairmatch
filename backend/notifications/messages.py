"""
The notification catalog of the spec: who receives each event and what it says.
Plain functions that build a `Message` from the row that caused the event, so the texts need no database to be tested.
The `delete` messages are built before the row is deleted, while its fields are still there.
"""
from dataclasses import dataclass

from django.utils import timezone

from hairmatch.local_time import LOCAL_TIMEZONE, make_local_aware

TITLE_MAX_LENGTH = 100
BODY_MAX_LENGTH = 300


@dataclass(frozen=True)
class Message:
    recipient: object  # users.User
    kind: str
    title: str
    body: str
    data: dict


def format_rating(value):
    """5.0 -> "5", 4.5 -> "4,5"."""
    if float(value).is_integer():
        return str(int(value))
    return f'{value:.1f}'.replace('.', ',')


def stars(value):
    return 'estrela' if value == 1 else 'estrelas'


def local_date_time(moment):
    """The `dd/mm` and `HH:MM` of the moment on the clock of the salons (America/Manaus)."""
    local = timezone.localtime(make_local_aware(moment), LOCAL_TIMEZONE)
    return local.strftime('%d/%m'), local.strftime('%H:%M')


def _full_name(user):
    return f'{user.first_name} {user.last_name}'


def _message(recipient, kind, title, body, data):
    # The column is shorter than a long service name plus two long names; an overflow must not undo the action.
    if len(body) > BODY_MAX_LENGTH:
        body = body[:BODY_MAX_LENGTH - 1] + '…'
    return Message(recipient=recipient, kind=kind, title=title, body=body, data=data)


def reservation_created(reserve):
    day, hour = local_date_time(reserve.start_time)
    return _message(
        reserve.service.hairdresser.user, 'reservation-created', 'Nova reserva',
        f'{_full_name(reserve.customer.user)} reservou {reserve.service.name} para {day} às {hour}.',
        {'reservation_id': reserve.pk},
    )


def review_created(review):
    return _message(
        review.hairdresser.user, 'review-created', 'Nova avaliação',
        f'{_full_name(review.customer.user)} avaliou seu atendimento com {format_rating(review.rating)} {stars(review.rating)}.',
        {'review_id': review.pk},
    )


def review_updated(review):
    return _message(
        review.hairdresser.user, 'review-updated', 'Avaliação atualizada',
        f'{_full_name(review.customer.user)} atualizou a avaliação do seu atendimento: '
        f'{format_rating(review.rating)} {stars(review.rating)}.',
        {'review_id': review.pk},
    )


def review_deleted(review):
    return _message(
        review.hairdresser.user, 'review-deleted', 'Avaliação removida',
        f'{_full_name(review.customer.user)} removeu a avaliação do seu atendimento.',
        {},
    )


def customer_rating_created(rating):
    return _message(
        rating.customer.user, 'customer-rating-created', 'Você foi avaliado',
        f'{_full_name(rating.hairdresser.user)} deu nota {format_rating(rating.rating)} para você.',
        {'customer_rating_id': rating.pk},
    )


def customer_rating_updated(rating):
    return _message(
        rating.customer.user, 'customer-rating-updated', 'Avaliação atualizada',
        f'{_full_name(rating.hairdresser.user)} mudou sua nota para {format_rating(rating.rating)}.',
        {'customer_rating_id': rating.pk},
    )


def customer_rating_deleted(rating):
    return _message(
        rating.customer.user, 'customer-rating-deleted', 'Avaliação removida',
        f'{_full_name(rating.hairdresser.user)} removeu a nota que deu a você.',
        {},
    )
