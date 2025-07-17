from rest_framework import serializers
from .models import Review
from users.models import User
from users.serializers import CustomerNameSerializer


class ReviewSerializer(serializers.ModelSerializer):
    customer = CustomerNameSerializer(read_only=True)
    class Meta:
        model = Review
        fields = '__all__'

class ReviewLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = '__all__'
    