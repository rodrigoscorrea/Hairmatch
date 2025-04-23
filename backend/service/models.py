from django.db import models

# Create your models here.

name = models.CharField(max_length=200, blank=False, null=False)
price = models.DecimalField(max_digits=6, decimal_places=2, blank=False, null=False)
duration = models.PositiveSmallIntegerField(blank=False, null=False)
