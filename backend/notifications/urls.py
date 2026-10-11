from django.urls import path
from notifications.views import AlertCollection, AlertDetail, PushDeviceCollection, PushDeviceDetail

urlpatterns = [
    path('users/me/push-devices', PushDeviceCollection.as_view(), name='push_devices'),
    path('users/me/push-devices/<int:device_id>', PushDeviceDetail.as_view(), name='push_device'),
    path('users/me/alerts', AlertCollection.as_view(), name='alerts'),
    path('users/me/alerts/<int:alert_id>', AlertDetail.as_view(), name='alert'),
]
