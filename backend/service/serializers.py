from service.models import Service
from users.serializers import HairdresserNameSerializer, HairdresserSerializer
from rest_framework import serializers

class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = '__all__'

class ServiceWithHairdresserSerializer(serializers.ModelSerializer):
    hairdresser = HairdresserNameSerializer(read_only=True)
    class Meta:
        model = Service
        fields = '__all__'

class ServiceWithHairdresserFullInfoSerializer(serializers.ModelSerializer):
    hairdresser = HairdresserSerializer(read_only=True)
    class Meta:
        model = Service
        fields = '__all__'