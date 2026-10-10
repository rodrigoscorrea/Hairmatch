"""
The hairdresser's rating of a customer (#104). `User.rating` of a customer is derived from these rows,
so every rating goes through `record_customer_rating`, which writes both in one transaction (AD-010).
"""
from django.db import IntegrityError, transaction
from django.db.models import Avg

from hairmatch.problems import Problem
from users.models import User

from .models import CustomerRating

ALREADY_RATED_DETAIL = 'This reservation has already been rated.'


def service_end(reservation):
    """When the reserved service ends (`start_time` plus the service's current duration), or None without a start."""
    # Imported here: reserve.views pulls serializers that import each other, and only work from a loaded app.
    from reserve.views import calculate_end_time

    if reservation.start_time is None:
        return None
    return calculate_end_time(reservation.start_time, reservation.service.duration)


def record_customer_rating(hairdresser, reservation, rating, comment):
    """
    Creates the rating of `reservation`'s customer and stores their new average in `User.rating`.
    Raises Problem('review-exists') when the reservation already has a rating.
    """
    with transaction.atomic():
        # Ratings of the same customer wait here for each other, so every average counts all of them.
        user = User.objects.select_for_update().get(pk=reservation.customer.user_id)
        try:
            # A savepoint: the IntegrityError of a concurrent duplicate must not break the outer transaction.
            with transaction.atomic():
                customer_rating = CustomerRating.objects.create(
                    reservation=reservation,
                    customer=reservation.customer,
                    hairdresser=hairdresser,
                    rating=rating,
                    comment=comment,
                )
        except IntegrityError:
            raise Problem('review-exists', ALREADY_RATED_DETAIL)

        average = CustomerRating.objects.filter(customer=reservation.customer).aggregate(Avg('rating'))['rating__avg']
        user.rating = round(average, 2)
        user.save(update_fields=['rating'])
    return customer_rating
