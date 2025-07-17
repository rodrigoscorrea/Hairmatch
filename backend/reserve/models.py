from django.db import models
from django.utils import timezone
from review.models import Review
from users.models import Customer
from service.models import Service

# Create your models here.
class Reserve(models.Model):
    start_time = models.DateTimeField(default=timezone.now, null=True, blank=True, unique=False)
    review = models.OneToOneField(Review, on_delete=models.DO_NOTHING, null=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.DO_NOTHING, null=False, blank=False)
    service = models.ForeignKey(Service,on_delete=models.DO_NOTHING, null=False, blank=False)
    #user = models.ForeignKey(User, related_name='reserves', null=False, blank=False)