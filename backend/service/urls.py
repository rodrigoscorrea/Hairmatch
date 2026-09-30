from django.urls import path
from .views import ListServiceHairdresser, ServiceCollection, ServiceDetail
urlpatterns = [
    path('services', ServiceCollection.as_view(), name='service_collection'),
    path('services/<int:service_id>', ServiceDetail.as_view(), name='service_detail'),
    path('hairdressers/<int:hairdresser_id>/services', ListServiceHairdresser.as_view(), name='list_service_hairdresser'),
]
