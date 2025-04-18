from rest_framework import serializers
from .models import User, Hairdresser, Customer

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name' ,'email', 'phone', 'street', 'number', 'postal_code', 'rating', 'role']

class HairdresserSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = Hairdresser
        fields = '__all__'

class CustomerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = Customer
        fields = '__all__'