from agenda.models import Agenda
from rest_framework import serializers
from users.serializers import HairdresserSerializer
from service.serializers import ServiceSerializer

class AgendaSerializer(serializers.ModelSerializer):
    hairdresser = HairdresserSerializer(read_only=True)
    service = ServiceSerializer(read_only=True)
    class Meta:
        model = Agenda
        fields = '__all__'