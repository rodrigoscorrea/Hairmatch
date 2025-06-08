from django.urls import path
from .views import EvolutionApi

urlpatterns = [
    path('test', EvolutionApi.as_view(), name='whastapp_chatbot'),
]