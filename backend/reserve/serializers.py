from reserve.models import Reserve
from rest_framework import serializers
from service.serializers import ServiceWithHairdresserSerializer

class ReserveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reserve
        fields = '__all__'

class ReserveFullInfoSerializer(serializers.ModelSerializer):
    service = ServiceWithHairdresserSerializer(read_only=True) 
    class Meta: 
        model = Reserve
        fields = '__all__'
