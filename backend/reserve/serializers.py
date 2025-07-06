from reserve.models import Reserve
from rest_framework import serializers
from service.serializers import ServiceWithHairdresserFullInfoSerializer
from review.serializers import ReviewLiteSerializer

class ReserveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reserve
        fields = '__all__'

class ReserveFullInfoSerializer(serializers.ModelSerializer):
    service = ServiceWithHairdresserFullInfoSerializer(read_only=True)
    review =  ReviewLiteSerializer(read_only=True)
    class Meta: 
        model = Reserve
        fields = '__all__'
