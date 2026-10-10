from django.db import models

from users.models import Customer, Hairdresser


class FavoriteHairdresser(models.Model):
    """A hairdresser a customer marked as favorite. The row goes with the account of either side."""
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='favorite_hairdressers')
    hairdresser = models.ForeignKey(Hairdresser, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Most recently favorited first; the id breaks a tie.
        ordering = ['-created_at', '-id']
        constraints = [
            models.UniqueConstraint(fields=['customer', 'hairdresser'], name='unique_favorite_hairdresser'),
        ]
