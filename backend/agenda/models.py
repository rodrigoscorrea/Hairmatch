from django.db import models
from users.models import Hairdresser
from django.utils import timezone
from service.models import Service

class Agenda(models.Model):
    start_time = models.DateTimeField(default=timezone.now, null=False, blank=False, unique=False)
    end_time = models.DateTimeField(default=timezone.now, null=False, blank=False, unique=False)
    hairdresser = models.ForeignKey(Hairdresser, on_delete=models.DO_NOTHING,null=False, blank=False)
    # NULL is an external block, which the hairdresser booked outside the app and names by `title`
    service = models.ForeignKey(Service, on_delete=models.DO_NOTHING, null=True, blank=True)
    title = models.CharField(max_length=100, blank=True, default='')
