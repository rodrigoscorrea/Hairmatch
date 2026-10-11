from django.db import models

from users.models import User


class PushDevice(models.Model):
    """A phone registered for push. The token is unique in the system: a phone belongs to one account at a time."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='push_devices')
    token = models.CharField(max_length=1024, unique=True)
    endpoint_arn = models.CharField(max_length=512)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Alert(models.Model):
    """A notification kept for its recipient, whether or not a push reached a phone."""
    KINDS = [
        'reservation-created',
        'review-created', 'review-updated', 'review-deleted',
        'customer-rating-created', 'customer-rating-updated', 'customer-rating-deleted',
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='alerts')
    kind = models.CharField(max_length=40, choices=[(kind, kind) for kind in KINDS])
    title = models.CharField(max_length=100)
    body = models.CharField(max_length=300)
    data = models.JSONField(default=dict)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Newest first; the id breaks a tie.
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['recipient', '-created_at'])]
