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

#
# HAIRDRESSERS SERIALIZERS 
#

class HairdresserSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = Hairdresser
        exclude = ('experience_time', 'products', 'experiences', 'experience_years') 

class HairdresserFullInfoSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = Hairdresser
        exclude = ['cnpj']

class HairdresserNameSerializer(serializers.ModelSerializer):
    user = UserNameSerializer(read_only=True)
    class Meta:
        model = Hairdresser
        fields = ['id', 'user']

#
# CUSTOMER SERIALIZERS 
#

class CustomerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class Meta:
        model = Customer
        fields = '__all__'

class CustomerNameSerializer(serializers.ModelSerializer):
    user = UserNameSerializer(read_only=True)
    class Meta:
        model = Customer
        fields = ['id', 'user']

# AI AIMED SERIALIZERS

class UserFullInfoSerializer(serializers.ModelSerializer):
    hairdresser = HairdresserSerializer(read_only=True)
    preferences = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['hairdresser','preferences'] 
    
    def get_preferences(self, obj):
        preferences = obj.preferences.all()
        return [preference.name for preference in preferences] 