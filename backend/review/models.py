from django.db import models
from hairmatch.images import WebPImageField
from users.models import User, Hairdresser, Customer


class Review(models.Model):
    rating = models.FloatField(blank=False, null=False)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    picture = WebPImageField(upload_to='reviews/images/', blank=True, null=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='reviews')
    hairdresser = models.ForeignKey(Hairdresser, on_delete=models.CASCADE, related_name='reviews')
    

class CustomerRating(models.Model):
    """A hairdresser's rating of the customer of one reservation. It is immutable once created."""
    # By string: reserve.models imports this module. SET_NULL so cancelling a reservation cannot erase its rating.
    reservation = models.OneToOneField(
        'reserve.Reserve', on_delete=models.SET_NULL, null=True, blank=True, related_name='customer_rating',
    )
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='received_ratings')
    # The rating is about the customer, so it outlives the account of the hairdresser who wrote it.
    hairdresser = models.ForeignKey(
        Hairdresser, on_delete=models.SET_NULL, null=True, blank=True, related_name='given_ratings',
    )
    rating = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(rating__gte=1) & models.Q(rating__lte=5), name='customer_rating_1_to_5',
            ),
        ]
