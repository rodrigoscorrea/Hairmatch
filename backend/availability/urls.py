from django.urls import path
from .views import CreateAvailability, CreateMultipleAvailability,ListAvailability, RemoveAvailability, UpdateAvailability, UpdateMultipleAvailability

urlpatterns = [
    path('create', CreateAvailability.as_view(), name='create_availability'),
    path('create/multiple/<int:hairdresser_id>', CreateMultipleAvailability.as_view(), name='create_multiple_availability'),
    path('list/<int:hairdresser_id>', ListAvailability.as_view(), name='list_availability'),
    path('remove/<int:id>', RemoveAvailability.as_view(), name='remove_availability'),
    path('update/multiple/<int:hairdresser_id>', UpdateMultipleAvailability.as_view(), name='update_multiple_availability'),
    path('update/<int:id>', UpdateAvailability.as_view(), name='update_availability'),
]