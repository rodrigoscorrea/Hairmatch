from agenda.models import Agenda
from rest_framework import serializers
from users.serializers import HairdresserSerializer
from service.serializers import ServiceSerializer
from users.models import User, Customer
from service.models import Service

class SimpleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name']

class SimpleCustomerSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer()
    class Meta:
        model = Customer
        fields = ['id', 'user']

class SimpleServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'name']

class AgendaSerializer(serializers.ModelSerializer):
    customer = serializers.SerializerMethodField()
    service = SimpleServiceSerializer() # Keep the nested service data

    class Meta:
        model = Agenda
        fields = ['id', 'start_time', 'end_time', 'service', 'customer'] # Add customer to fields

    def get_customer(self, obj: Agenda):
        """
        Looks for a customer in the pre-fetched data passed through the context.
        This avoids hitting the database for every single agenda item.
        """
        # Create a unique key for the current agenda item
        lookup_key = (obj.service_id, obj.start_time)
        
        # Get the reserve_map we created in the view from the context
        reserve_map = self.context.get('reserve_map', {})
        
        # Find the matching reserve in our map
        matching_reserve = reserve_map.get(lookup_key)

        if matching_reserve:
            # If we found a match, serialize its customer
            return SimpleCustomerSerializer(matching_reserve.customer).data
        
        # Return null if no corresponding reserve was found
        return None