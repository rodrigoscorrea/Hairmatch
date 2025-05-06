from django.urls import path
from .views import CreateReserve, ListReserve, UpdateReserve, RemoveReserve, ReserveSlot

urlpatterns = [
    path('create', CreateReserve.as_view(), name='create_reserve'),
    path('slots/<int:hairdresser_id>', ReserveSlot.as_view(), name="get_slots"),
    path('list/<int:customer_id>', ListReserve.as_view(), name='list_reserve'),
    path('list', ListReserve.as_view(), name='list_reserve'),
    #path('update/<int:reserve_id>', UpdateReserve.as_view(), name='update_reserve'),
    path('remove/<int:reserve_id>', RemoveReserve.as_view(), name='remove_reserve'),
]