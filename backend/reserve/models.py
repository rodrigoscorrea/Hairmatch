from django.db import models
from django.utils import timezone
from review.models import Review
from users.models import Customer, Hairdresser, User

# Create your models here.
class Reserve(models.Model):
    created_at = models.DateTimeField(default=timezone.now)
    review = models.ForeignKey(Review, related_name='reserves', null=True, blank=True)
    #customer = models.ForeignKey(Customer, related_name='reservers', null=False, blank=False)
    #hairdresser = models.ForeignKey(Hairdresser, related_name='reservers', null=False, blank=False)
    user = models.ForeignKey(User, related_name='reserves', null=False, blank=False)