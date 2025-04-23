from django.urls import path
from .views import CreateReserve, ListReserve, UpdateReserve, RemoveReserve

urlpatterns = [
    path('create', CreateReserve.as_view(), name='create_reserve'),
    path('list/<int:user_id>', ListReserve.as_view(), name='list_reserve'),
    path('update/<int:reserve_id>', UpdateReserve.as_view(), name='update_reserve'),
    path('remove/<int: reserve_id>', RemoveReserve.as_view(), name='remove_reserve'),
]