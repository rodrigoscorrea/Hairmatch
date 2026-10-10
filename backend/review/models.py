import os
import uuid

from django.db import models
from hairmatch.images import WebPImageField
from users.models import User, Hairdresser, Customer


def review_picture_path(instance, filename):
    # A fresh name per picture: two uploads called "foto.jpg" must not collide or be renamed by the storage.
    # `review_id` and not `review.pk`: the picture has no pk of its own yet when the file is saved.
    return f"reviews/{instance.review_id}/{uuid.uuid4().hex}{os.path.splitext(filename)[1]}"


class Review(models.Model):
    rating = models.FloatField(blank=False, null=False)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    picture = WebPImageField(upload_to='reviews/images/', blank=True, null=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='reviews')
    hairdresser = models.ForeignKey(Hairdresser, on_delete=models.CASCADE, related_name='reviews')


class ReviewPicture(models.Model):
    """One picture of a review. A review has at most 5 (enforced by the views, with the review row locked)."""
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='pictures')
    picture = WebPImageField(upload_to=review_picture_path)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']


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
