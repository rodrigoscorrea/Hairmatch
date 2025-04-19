from django.urls import path
from .views import CreateAvailability, ListAvailability, RemoveAvailability, UpdateAvailability

urlpatterns = [
    path('create', CreateAvailability.as_view(), name='create_availability'),
    path('list/<int:hairdresser_id>', ListAvailability.as_view(), name='list_availability'),
    path('remove/<int:id>', RemoveAvailability.as_view(), name='remove_availability'),
    path('update/<int:id>', UpdateAvailability.as_view(), name='update_availability'),
]