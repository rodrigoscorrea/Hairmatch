from agenda.models import Agenda
from rest_framework import serializers
from users.serializers import HairdresserSerializer
from service.serializers import ServiceSerializer
from users.models import User, Customer
from service.models import Service

class SimpleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'rating']

class SimpleCustomerSerializer(serializers.ModelSerializer):
    user = SimpleUserSerializer()
    ratings_count = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = ['id', 'user', 'ratings_count']

    def get_ratings_count(self, obj):
        # Counted for every customer of the agenda in one query by the view.
        return self.context.get('ratings_count_by_customer', {}).get(obj.id, 0)

class SimpleServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'name']

class AgendaSerializer(serializers.ModelSerializer):
    customer = serializers.SerializerMethodField()
    service = SimpleServiceSerializer() # Keep the nested service data
    reservation_id = serializers.SerializerMethodField()
    customer_rating = serializers.SerializerMethodField()

    class Meta:
        model = Agenda
        fields = ['id', 'start_time', 'end_time', 'service', 'customer', 'reservation_id', 'customer_rating']

    def _reserve(self, obj: Agenda):
        return self.context.get('reserve_map', {}).get((obj.service_id, obj.start_time))

    def get_reservation_id(self, obj: Agenda):
        reserve = self._reserve(obj)
        return reserve.id if reserve else None

    def get_customer_rating(self, obj: Agenda):
        """The hairdresser's rating of this reservation's customer, or None while it is not rated."""
        # The reverse one-to-one raises an AttributeError subclass when the reservation has no rating.
        rating = getattr(self._reserve(obj), 'customer_rating', None)
        return {'rating': rating.rating, 'comment': rating.comment} if rating else None

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
            return SimpleCustomerSerializer(matching_reserve.customer, context=self.context).data
        
        # Return null if no corresponding reserve was found
        return None