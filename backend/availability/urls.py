from django.urls import path
from .views import CreateAvailability, HairdresserAvailabilities, AvailabilityDetail

urlpatterns = [
    path('availabilities', CreateAvailability.as_view(), name='create_availability'),
    path('availabilities/<int:id>', AvailabilityDetail.as_view(), name='availability_detail'),
    path('hairdressers/<int:hairdresser_id>/availabilities', HairdresserAvailabilities.as_view(), name='hairdresser_availabilities'),
]
