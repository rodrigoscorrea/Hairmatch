from django.shortcuts import render
from agenda.models import Agenda
from agenda.serializers import AgendaSerializer
from users.models import User, Hairdresser
from service.models import Service
from rest_framework.views import APIView
from django.http import HttpResponse, JsonResponse
import json
from datetime import timedelta, datetime
from reserve.models import Reserve
from django.db.models import Q
from django.utils import timezone
from users.authentication import authenticated_hairdresser, forbidden
from hairmatch.local_time import make_local_aware
from hairmatch.problems import body_error, json_object, problem_response, validation_problem
# Create your views here.

DATETIME_FORMAT_DETAIL = 'The value must be an ISO 8601 datetime.'
TITLE_MAX_LENGTH = Agenda._meta.get_field('title').max_length


def _parse_local_datetime(value):
    """An ISO 8601 string as an aware datetime (a naive one is Manaus time), or None when it is not one."""
    try:
        return make_local_aware(datetime.fromisoformat(value.replace('Z', '+00:00')))
    except (ValueError, TypeError, AttributeError):
        return None


class CreateAgenda(APIView):
    def post(self, request):
        # Blocks a slot in the session hairdresser's own agenda; a `hairdresser` in the body is ignored.
        session, hairdresser_instance, error = authenticated_hairdresser(request)
        if error:
            return error

        data = json_object(request)
        # Without a service the entry is an external block: the end time and a title are then required.
        has_service = bool(data.get('service'))
        errors = []
        start_time = end_time = None
        if not data.get('start_time'):
            errors.append(body_error('start_time', 'This field is required.'))
        else:
            start_time = _parse_local_datetime(data['start_time'])
            if start_time is None:
                errors.append(body_error('start_time', DATETIME_FORMAT_DETAIL))
            elif start_time < timezone.now():
                errors.append(body_error('start_time', 'The start time must not be in the past.'))
        if data.get('end_time'):
            end_time = _parse_local_datetime(data['end_time'])
            if end_time is None:
                errors.append(body_error('end_time', DATETIME_FORMAT_DETAIL))
            elif start_time is not None and end_time <= start_time:
                errors.append(body_error('end_time', 'The end time must be after the start time.'))
        elif not has_service:
            errors.append(body_error('end_time', 'This field is required.'))
        # A null title is read as an absent one
        title = data.get('title')
        if title is None:
            title = ''
        if not isinstance(title, str):
            errors.append(body_error('title', 'This field must be a string.'))
        else:
            title = title.strip()
            if len(title) > TITLE_MAX_LENGTH:
                errors.append(body_error('title', f'Ensure this field has no more than {TITLE_MAX_LENGTH} characters.'))
            elif not title and not has_service:
                errors.append(body_error('title', 'This field is required.'))
        if errors:
            raise validation_problem(errors)

        service_instance = None
        if has_service:
            try:
                service_instance = Service.objects.get(id=data['service'])
            except (Service.DoesNotExist, ValueError, TypeError):
                return problem_response(request, 'not-found', 'Service not found.')
            if service_instance.hairdresser_id != hairdresser_instance.id:
                return forbidden(request)

            # Calculate end_time if not provided
            if end_time is None:
                end_time = start_time + timedelta(minutes=service_instance.duration)

        # Full overlap check:
        # Checks whether there are appointments that overlap with the new appointment
        overlapping_agendas = Agenda.objects.filter(
            hairdresser=hairdresser_instance,
            # The existing appointment's start_time is before the new one's end_time
            start_time__lt=end_time,
            # And the existing appointment's end_time is after the new one's start_time
            end_time__gt=start_time
        )

        if overlapping_agendas.exists():
            return problem_response(request, 'agenda-overlap', 'This time slot overlaps with an existing appointment.')

        # It's now safe to create the appointment
        Agenda.objects.create(
            service=service_instance,
            title=title,
            hairdresser=hairdresser_instance,
            start_time=start_time,
            end_time=end_time
        )

        return JsonResponse({'message': 'Agenda register created successfully'}, status=201)

class ListAgenda(APIView):
    def get(self, request, hairdresser_id=None):
        # The agenda names the customers, so only its hairdresser sees it; `list` without an id lists it too.
        session, hairdresser, error = authenticated_hairdresser(request)
        if error:
            return error
        if hairdresser_id is not None and hairdresser_id != hairdresser.id:
            return forbidden(request)

        agenda_items = Agenda.objects.filter(hairdresser=hairdresser).select_related('service')
        if not agenda_items.exists():
            return JsonResponse({'data': []}, status=200)
        # An external block (no service) never pairs with a reserve
        reserve_identifiers = set()
        for item in agenda_items:
            if item.service_id is not None:
                reserve_identifiers.add((item.service_id, item.start_time))

        reserve_map = {}
        if reserve_identifiers:
            q_objects = Q()
            for service_id, start_time in reserve_identifiers:
                q_objects |= Q(service_id=service_id, start_time=start_time)
            matching_reserves = Reserve.objects.filter(q_objects).select_related('customer__user')
            reserve_map = {
                (reserve.service_id, reserve.start_time): reserve
                for reserve in matching_reserves
            }
        serializer_context = {'reserve_map': reserve_map}
        serializer = AgendaSerializer(agenda_items, many=True, context=serializer_context)

        return JsonResponse({'data': serializer.data}, status=200)
    
class UpdateAgenda(APIView):
    def put(self, request, agenda_id):
        pass

class RemoveAgenda(APIView):
    def delete(self, request, agenda_id):
        session, hairdresser, error = authenticated_hairdresser(request)
        if error:
            return error

        try:
            agenda = Agenda.objects.get(id=agenda_id)
        except Agenda.DoesNotExist:
            return problem_response(request, 'not-found', 'Agenda slot not found.')
        if agenda.hairdresser_id != hairdresser.id:
            return forbidden(request)

        agenda.delete()
        return HttpResponse(status=204)


class AgendaCollection(ListAgenda, CreateAgenda):
    """`/api/agenda`: GET lists the logged hairdresser's agenda and POST adds an entry to it."""
