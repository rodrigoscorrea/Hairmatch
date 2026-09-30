from django.urls import path
from .views import AgendaCollection, ListAgenda, RemoveAgenda
urlpatterns = [
    path('agenda', AgendaCollection.as_view(), name='agenda_collection'),
    path('agenda/<int:agenda_id>', RemoveAgenda.as_view(), name='agenda_detail'),
    path('hairdressers/<int:hairdresser_id>/agenda', ListAgenda.as_view(), name='hairdresser_agenda'),
]
