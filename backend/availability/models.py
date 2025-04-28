from django.db import models
from users.models import Hairdresser

# Create your models here.

class Availability(models.Model):

    weekday = models.CharField(max_length=10, blank=False, null=False)
    hairdresser = models.ForeignKey(Hairdresser, on_delete=models.CASCADE, related_name='availability')
    start_time = models.TimeField(blank=False, null=False)
    end_time = models.TimeField(blank=False, null=False)
    break_start = models.TimeField(null=True, blank=True)
    break_end = models.TimeField(null=True, blank=True)
