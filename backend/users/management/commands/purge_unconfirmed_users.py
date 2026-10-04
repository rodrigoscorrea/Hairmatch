import logging
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from users.cognito import CognitoError, get_cognito
from users.models import User

logger = logging.getLogger(__name__)

# The confirmation code lasts 24 h and can be requested again; a week covers whoever is slow to open the e-mail.
PENDING_ACCOUNT_MAX_AGE = timedelta(days=7)


class Command(BaseCommand):
    """
    Deletes the e-mail accounts that never confirmed their address, in Cognito and then in Postgres,
    so a Cognito outage keeps the row and the next run tries again.
    """

    help = "Deletes accounts left pending e-mail confirmation for more than seven days"

    def handle(self, *args, **options):
        cutoff = timezone.now() - PENDING_ACCOUNT_MAX_AGE
        expired = User.objects.filter(is_active=False, cognito_sub__isnull=False, date_joined__lt=cutoff)
        cognito = get_cognito()
        deleted = kept = 0
        for user in expired:
            try:
                cognito.admin_delete_user(user.email)
            except CognitoError as error:
                logger.warning('purge kept user %s: %s', user.id, error.code)
                kept += 1
                continue
            user.delete()
            deleted += 1

        summary = f'purge_unconfirmed_users deleted={deleted} kept={kept}'
        logger.info(summary)
        # The boot log only shows warnings from the logging module, so the summary is printed as well.
        self.stdout.write(summary)
