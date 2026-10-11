from django.db import IntegrityError, transaction
from django.http import HttpResponse, JsonResponse
from rest_framework.views import APIView

from hairmatch.problems import Problem, body_error, json_object, problem_response, validation_problem
from users.authentication import authenticated_user

from .dispatch import delete_endpoints
from .models import PushDevice
from .sns import PushUnavailable, get_sns

TOKEN_MAX_LENGTH = 1024
TOKEN_DETAIL = f'The token must be a text of 1 to {TOKEN_MAX_LENGTH} characters.'
PUSH_UNAVAILABLE_DETAIL = 'The push service is unavailable. Try again shortly.'
# A POST that loses the race for a new token reads the winner's row on the next turn; a few turns are plenty.
REGISTER_ATTEMPTS = 3


def _token(data):
    token = data.get('token')
    if not isinstance(token, str) or not 0 < len(token.strip()) <= TOKEN_MAX_LENGTH:
        raise validation_problem([body_error('token', TOKEN_DETAIL)])
    return token.strip()


def _register(user, token):
    """Returns (device, created): the row of `token` for `user`, and whether the phone is new to the account."""
    arn = None
    for _ in range(REGISTER_ATTEMPTS):
        with transaction.atomic():
            device = PushDevice.objects.select_for_update().filter(token=token).first()
            if device is not None:
                if device.user_id == user.id:
                    return device, False
                # The phone changed hands. Its endpoint belongs to the token, so the ARN stays.
                device.user = user
                device.save(update_fields=['user', 'updated_at'])
                return device, True
        # Outside any lock: SNS can be slow, and a row that does not exist yet cannot be locked anyway.
        if arn is None:
            try:
                arn = get_sns().create_endpoint(token)
            except PushUnavailable:
                raise Problem('push-unavailable', PUSH_UNAVAILABLE_DETAIL)
        try:
            with transaction.atomic():
                return PushDevice.objects.create(user=user, token=token, endpoint_arn=arn), True
        except IntegrityError:
            # A simultaneous POST stored the token first; the next turn finds its row.
            continue
    raise Problem('push-unavailable', PUSH_UNAVAILABLE_DETAIL)


class PushDeviceCollection(APIView):
    def post(self, request):
        session, error = authenticated_user(request)
        if error:
            return error

        token = _token(json_object(request))
        device, created = _register(session.user, token)

        return JsonResponse({'data': {'id': device.id}}, status=201 if created else 200)


class PushDeviceDetail(APIView):
    def delete(self, request, device_id):
        session, error = authenticated_user(request)
        if error:
            return error

        with transaction.atomic():
            device = PushDevice.objects.filter(pk=device_id, user=session.user).first()
            if device is None:
                return problem_response(request, 'not-found', 'Push device not found.')
            arn = device.endpoint_arn
            device.delete()
            # After the commit and without a guarantee: the row is gone, so a failure only goes to the log.
            transaction.on_commit(lambda: delete_endpoints([arn]), robust=True)

        return HttpResponse(status=204)
