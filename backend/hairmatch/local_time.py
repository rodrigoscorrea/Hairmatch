from datetime import datetime
from zoneinfo import ZoneInfo

from django.utils import timezone

# The salons' timezone. Opening hours, slots and the times typed in the app or the chatbot are in this clock.
LOCAL_TIMEZONE = ZoneInfo('America/Manaus')


def make_local_aware(dt):
    """A naive datetime is a Manaus wall-clock time; an aware one is kept as is."""
    if timezone.is_naive(dt):
        return timezone.make_aware(dt, LOCAL_TIMEZONE)
    return dt


def local_day_bounds(day):
    """Aware start and end of the given Manaus calendar day."""
    start = timezone.make_aware(datetime.combine(day, datetime.min.time()), LOCAL_TIMEZONE)
    end = timezone.make_aware(datetime.combine(day, datetime.max.time()), LOCAL_TIMEZONE)
    return start, end


def local_today():
    return timezone.localtime(timezone.now(), LOCAL_TIMEZONE).date()
