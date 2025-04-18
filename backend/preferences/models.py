from django.db import models
from users.models import User

# Create your models here.

class Preferences(models.Model):
    name = models.CharField(max_length=100, blank=False, null=False)
    picture = models.ImageField(upload_to='preferences/images/', blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, to_field="id", related_name='preferences')

