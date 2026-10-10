from rest_framework import serializers
from .models import CustomerRating, Review, ReviewPicture
from users.models import User
from users.serializers import CustomerNameSerializer


class ReviewPictureSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = ReviewPicture
        fields = ['id', 'url']

    def get_url(self, obj):
        return obj.picture.url


class ReviewSerializer(serializers.ModelSerializer):
    customer = CustomerNameSerializer(read_only=True)
    pictures = ReviewPictureSerializer(many=True, read_only=True)
    class Meta:
        model = Review
        fields = '__all__'

class ReviewLiteSerializer(serializers.ModelSerializer):
    pictures = ReviewPictureSerializer(many=True, read_only=True)

    class Meta:
        model = Review
        fields = '__all__'


class CustomerRatingCreatedSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerRating
        fields = ['id', 'reservation', 'rating', 'comment', 'created_at']


class CustomerRatingSerializer(serializers.ModelSerializer):
    """A rating as the customer's list shows it. The names are null once the reservation or the author is gone."""
    service_name = serializers.SerializerMethodField()
    hairdresser_name = serializers.SerializerMethodField()

    class Meta:
        model = CustomerRating
        fields = ['id', 'rating', 'comment', 'created_at', 'service_name', 'hairdresser_name']

    def get_service_name(self, obj):
        return obj.reservation.service.name if obj.reservation else None

    def get_hairdresser_name(self, obj):
        if obj.hairdresser is None:
            return None
        return f'{obj.hairdresser.user.first_name} {obj.hairdresser.user.last_name}'
