"""
The one way to notify a user (AD-014): `notify` keeps an alert in the transaction of the action
and publishes the push after the commit. Nothing here may make the action fail.
"""
import logging

from django.db import transaction

from .models import Alert, PushDevice
from .sns import EndpointGone, get_sns

logger = logging.getLogger(__name__)


def notify(message, actor=None):
    """
    Saves the alert and schedules its push for after the commit. Returns the alert,
    or None when the author of the action is the recipient (nobody notifies themselves).
    """
    if actor is not None and message.recipient == actor:
        return None
    alert = Alert.objects.create(
        recipient=message.recipient, kind=message.kind, title=message.title, body=message.body, data=message.data,
    )
    # Outside an atomic block this runs at once. `robust` keeps an error here from reaching the view after the commit.
    transaction.on_commit(lambda: publish_alert(alert.pk), robust=True)
    return alert


def publish_alert(alert_id):
    """Pushes the alert to every phone its recipient owns now. A failure is logged and never raised."""
    try:
        alert = Alert.objects.filter(pk=alert_id).first()
        if alert is None:
            return
        data = {'alert_id': str(alert.pk), 'kind': alert.kind}
        # Read at the moment of the send: a phone that changed hands since the alert was saved belongs to its new owner.
        for device in PushDevice.objects.filter(user_id=alert.recipient_id):
            try:
                get_sns().publish(device.endpoint_arn, alert.title, alert.body, data)
            except EndpointGone:
                device.delete()
                delete_endpoints([device.endpoint_arn])
            except Exception as exc:
                # The token and the ARN stay out of the log. SNS errors were already logged with the operation and the code.
                logger.warning('push to a device failed: %s', type(exc).__name__)
    except Exception as exc:
        logger.warning('push of alert %s failed: %s', alert_id, type(exc).__name__)


def delete_endpoints(arns):
    """Removes the endpoints from SNS without a guarantee: the rows are gone, so a failure only goes to the log."""
    for arn in arns:
        try:
            get_sns().delete_endpoint(arn)
        except Exception as exc:
            logger.warning('deleting a push endpoint failed: %s', type(exc).__name__)
