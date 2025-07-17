from rest_framework import serializers
from .models import User, Hairdresser, Customer

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'email', 'phone', 
            'address', 'number', 'postal_code', 'rating', 'role',
            'complement', 'neighborhood', 'city', 'state', 'profile_picture'
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

#
# SEARCH RESULT SERIALIZER
#

from .models import Hairdresser # Make sure models are imported
from service.models import Service
from service.serializers import ServiceWithHairdresserSerializer

class SearchResultSerializer(serializers.BaseSerializer):
    """
    A custom serializer to handle heterogeneous search results.
    
    It inspects the type of the object and uses the appropriate specific
    serializer, adding a 'result_type' field to the output.
    """
    def to_representation(self, instance):
        # Check if the instance is a Hairdresser model
        if isinstance(instance, Hairdresser):
            # Use the HairdresserSerializer to serialize the object
            serializer = HairdresserSerializer(instance, context=self.context)
            data = serializer.data
            # Add a type identifier for the frontend
            data['result_type'] = 'hairdresser'
            return data
        
        # Check if the instance is a Service model
        elif isinstance(instance, Service):
            # Use the ServiceSerializer to serialize the object
            serializer = ServiceWithHairdresserSerializer(instance, context=self.context)
            data = serializer.data
            # Add a type identifier for the frontend
            data['result_type'] = 'service'
            return data
            
        # If the object type is unknown, raise an error.
        raise Exception(f"Unknown type for SearchResultSerializer: {type(instance).__name__}")

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