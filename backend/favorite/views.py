from django.http import HttpResponse
from rest_framework.views import APIView

from hairmatch.problems import problem_response
from users.authentication import authenticated_customer
from users.models import Hairdresser

from .models import FavoriteHairdresser


class FavoriteHairdresserDetail(APIView):
    """PUT favorites and DELETE unfavorites a hairdresser for the logged customer. Both are idempotent and answer 204."""

    def put(self, request, hairdresser_id):
        session, customer, error = authenticated_customer(request)
        if error:
            return error

        # A pending account (AD-008) is out of every listing, so it cannot be favorited.
        hairdresser = Hairdresser.objects.filter(id=hairdresser_id, user__is_active=True).first()
        if not hairdresser:
            return problem_response(request, 'not-found', 'Hairdresser not found.')

        # get_or_create relies on the unique pair: two simultaneous requests end with one row, and the older created_at stays.
        FavoriteHairdresser.objects.get_or_create(customer=customer, hairdresser=hairdresser)

        return HttpResponse(status=204)

    def delete(self, request, hairdresser_id):
        session, customer, error = authenticated_customer(request)
        if error:
            return error

        # No is_active filter: unfavoriting is never blocked for a hairdresser that exists.
        hairdresser = Hairdresser.objects.filter(id=hairdresser_id).first()
        if not hairdresser:
            return problem_response(request, 'not-found', 'Hairdresser not found.')

        FavoriteHairdresser.objects.filter(customer=customer, hairdresser=hairdresser).delete()

        return HttpResponse(status=204)
