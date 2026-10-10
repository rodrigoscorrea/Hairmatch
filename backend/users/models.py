# Create your models here.

import uuid

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.conf import settings

from hairmatch.images import WebPImageField


GALLERY_MAX_PHOTOS = 30


def user_profile_picture_path(instance, filename):
    # Each user gets its own directory in the media bucket
    return f"profile_pics/{instance.pk}/{filename}"


def gallery_photo_path(instance, filename):
    # One directory per hairdresser; the name is random so the original filename never reaches the bucket.
    return f"hairdresser/gallery/{instance.hairdresser_id}/{uuid.uuid4().hex}.webp"


class User(AbstractUser):
    first_name = models.CharField(max_length=100, blank=False, null=False)
    last_name = models.CharField(max_length=100,  blank=False, null=False)
    
    email = models.EmailField(max_length=255,unique=True, blank=False, null=False)
    password = models.CharField(max_length=255, blank=True, null=True)
    phone= models.CharField(max_length=20, unique=True, blank=False, null=False)

    complement = models.CharField(max_length=150, blank=True, null=True)
    neighborhood = models.CharField(max_length=150, blank=False, null=False)
    city = models.CharField(max_length=150, blank=False, null=False)
    state = models.CharField(max_length=2, blank=False, null=False)
    address = models.CharField(max_length=150,  blank=False, null=False)
    number = models.CharField(max_length=6, blank=True, null=True)
    postal_code = models.CharField(max_length=10,  blank=False, null=False)

    rating = models.FloatField(blank=True, null=True, default=5)
    username = None
    
    USERNAME_FIELD='email'
    REQUIRED_FIELDS=[]

    ROLES_CHOICES = (
        ('CUSTOMER','customer'),
        ('HAIRDRESSER','hairdresser')
    )
    profile_picture = WebPImageField(upload_to=user_profile_picture_path, null=True, blank=True)
    role = models.CharField(max_length=12, choices=ROLES_CHOICES, default='CUSTOMER')
    google_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    cognito_sub = models.CharField(max_length=255, unique=True, null=True, blank=True)

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


class GalleryPhoto(models.Model):
    hairdresser = models.ForeignKey(Hairdresser, on_delete=models.CASCADE, related_name='gallery_photos')
    image = WebPImageField(upload_to=gallery_photo_path)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['hairdresser', '-created_at'], name='gallery_hairdresser_created')]
