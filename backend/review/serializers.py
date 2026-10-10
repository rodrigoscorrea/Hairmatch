from rest_framework import serializers
from .models import CustomerRating, Review
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


class CustomerRatingCreatedSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerRating
        fields = ['id', 'reservation', 'rating', 'comment', 'created_at']
