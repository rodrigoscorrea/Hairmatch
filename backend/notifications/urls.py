from django.urls import path
from notifications.views import PushDeviceCollection, PushDeviceDetail

urlpatterns = [
    path('users/me/push-devices', PushDeviceCollection.as_view(), name='push_devices'),
    path('users/me/push-devices/<int:device_id>', PushDeviceDetail.as_view(), name='push_device'),
]
