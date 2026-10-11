from rest_framework import serializers

from .models import Alert


class AlertSerializer(serializers.ModelSerializer):
    read = serializers.SerializerMethodField()

    class Meta:
        model = Alert
        fields = ['id', 'kind', 'title', 'body', 'data', 'read', 'created_at']

    def get_read(self, obj):
        return obj.read_at is not None
