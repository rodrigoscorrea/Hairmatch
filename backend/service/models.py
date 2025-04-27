from django.db import models
from users.models import Hairdresser

# Create your models here.
class Service(models.Model):
    name = models.CharField(max_length=200, blank=False, null=False)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=6, decimal_places=2, blank=False, null=False)
    duration = models.PositiveSmallIntegerField(blank=False, null=False)
    hairdresser = models.ForeignKey(Hairdresser, on_delete=models.DO_NOTHING,null=False, blank=False)
