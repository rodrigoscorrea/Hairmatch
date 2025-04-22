from rest_framework import serializers
from .models import User, Hairdresser, Customer

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone', 
            'address', 'number', 'postal_code', 'rating', 'role',
            'complement', 'neighborhood', 'city', 'state'
        ]

class UserNameSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name']

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

class HairdresserNameSerializer(serializers.ModelSerializer):
    user = UserNameSerializer(read_only=True)
    class Meta:
        model = Hairdresser
        fields = ['id', 'user']

class CustomerNameSerializer(serializers.ModelSerializer):
    user = UserNameSerializer(read_only=True)
    class Meta:
        model = Customer
        fields = ['id', 'user']