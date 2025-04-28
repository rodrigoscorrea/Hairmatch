from django.db import models
from users.models import User, Hairdresser, Customer


class Review(models.Model):
    rating = models.FloatField(blank=False, null=False)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    picture = models.ImageField(upload_to='reviews/images/', blank=True, null=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='reviews')
    hairdresser = models.ForeignKey(Hairdresser, on_delete=models.CASCADE, related_name='reviews')
    