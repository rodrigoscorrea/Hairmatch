from django.urls import path
from .views import ListAgenda, CreateAgenda, RemoveAgenda
urlpatterns = [
    path('create', CreateAgenda.as_view(), name='create_agenda'),
    path('list/<int:hairdresser_id>', ListAgenda.as_view(), name='list_agenda'),
    path('list', ListAgenda.as_view(), name='list_agenda'),
    #path('update/<int:agenda_id>', UpdateAgenda.as_view(), name='update_agenda'),
    path('remove/<int:agenda_id>', RemoveAgenda.as_view(), name='remove_agenda'),
]