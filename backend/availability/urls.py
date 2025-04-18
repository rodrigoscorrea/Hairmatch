from django.urls import path
from .views import RegisterAvailability, ListAvailability, RemoveAvailability, UpdateAvailability

urlpatterns = [
    path('register', RegisterAvailability.as_view(), name='register_availability'),
    path('list/<int:id>', ListAvailability.as_view(), name='list_availability'),
    path('remove/<int:id>', RemoveAvailability.as_view(), name='remove_availability'),
    path('update/<int:id>', UpdateAvailability.as_view(), name='update_availability'),
]