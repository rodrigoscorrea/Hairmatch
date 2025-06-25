# Create your models here.

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.conf import settings

class User(AbstractUser):
    first_name = models.CharField(max_length=100, blank=False, null=False)
    last_name = models.CharField(max_length=100,  blank=False, null=False)
    
    email = models.EmailField(max_length=255,unique=True, blank=False, null=False)
    password = models.CharField(max_length=255, blank=True, null=True)
    phone= models.CharField(max_length=20, blank=False, null=False)

    complement = models.CharField(max_length=150, blank=True, null=True)
    neighborhood = models.CharField(max_length=150, blank=False, null=False)
    city = models.CharField(max_length=150, blank=False, null=False)
    state = models.CharField(max_length=2, blank=False, null=False)
    address = models.CharField(max_length=150,  blank=False, null=False)
    number = models.CharField(max_length=6, blank=True, null=True)
    postal_code = models.CharField(max_length=10,  blank=False, null=False)

    rating = models.PositiveSmallIntegerField(blank=True, null=True, default=5)
    username = None
    
    USERNAME_FIELD='email'
    REQUIRED_FIELDS=[]

    ROLES_CHOICES = (
        ('CUSTOMER','customer'),
        ('HAIRDRESSER','hairdresser')
    )

    role = models.CharField(max_length=12, choices=ROLES_CHOICES, default='CUSTOMER')

    def __str__(self):
        return self.email


class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    cpf = models.CharField(max_length=11, blank=False, null=False)


class Hairdresser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    experience_years = models.IntegerField(blank=True, null=True)
    resume = models.TextField(blank=True, null=True)
    cnpj = models.CharField(max_length=14, blank=False, null=False)
    experience_time = models.CharField(max_length=255, blank=True, null=True)
    experiences = models.CharField(max_length=255, blank=True, null=True)
    products = models.CharField(max_length=255, blank=True, null=True)