from rest_framework import serializers
from .models import Availability

class AvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Availability
        fields = ['id', 'weekday', 'start_time', 'end_time', 'break_start', 'break_end']