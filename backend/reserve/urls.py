from django.urls import path
from .views import ReservationCollection, ReservationDetail, ListReserve, ReserveSlot

urlpatterns = [
    path('reservations', ReservationCollection.as_view(), name='reservation_collection'),
    path('reservations/<int:id>', ReservationDetail.as_view(), name='reservation_detail'),
    path('customers/<int:customer_id>/reservations', ListReserve.as_view(), name='customer_reservations'),
    path('hairdressers/<int:hairdresser_id>/available-slots', ReserveSlot.as_view(), name='get_slots'),
]
