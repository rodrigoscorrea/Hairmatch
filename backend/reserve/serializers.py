from reserve.models import Reserve
from rest_framework import serializers

class ReserveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reserve
        fields = '__all__'