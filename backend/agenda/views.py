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
from django.db.models import Count, Q
from review.models import CustomerRating
from users.authentication import authenticated_hairdresser, forbidden
from hairmatch.local_time import make_local_aware
from hairmatch.problems import body_error, json_object, problem_response, validation_problem
# Create your views here.

DATETIME_FORMAT_DETAIL = 'The value must be an ISO 8601 datetime.'


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
        errors = []
        start_time = end_time = None
        if not data.get('start_time'):
            errors.append(body_error('start_time', 'This field is required.'))
        else:
            start_time = _parse_local_datetime(data['start_time'])
            if start_time is None:
                errors.append(body_error('start_time', DATETIME_FORMAT_DETAIL))
        if data.get('end_time'):
            end_time = _parse_local_datetime(data['end_time'])
            if end_time is None:
                errors.append(body_error('end_time', DATETIME_FORMAT_DETAIL))
        if not data.get('service'):
            errors.append(body_error('service', 'This field is required.'))
        if errors:
            raise validation_problem(errors)

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
        reserve_identifiers = set()
        for item in agenda_items:
            reserve_identifiers.add((item.service_id, item.start_time))

        q_objects = Q()
        for service_id, start_time in reserve_identifiers:
            q_objects |= Q(service_id=service_id, start_time=start_time)
        matching_reserves = Reserve.objects.filter(q_objects).select_related('customer__user', 'customer_rating')
        reserve_map = {
            (reserve.service_id, reserve.start_time): reserve
            for reserve in matching_reserves
        }
        # One grouped query, so the agenda costs the same number of queries for any number of customers.
        ratings_count_by_customer = dict(
            CustomerRating.objects.filter(customer_id__in={reserve.customer_id for reserve in reserve_map.values()})
            .values('customer_id')
            .annotate(total=Count('id'))
            .values_list('customer_id', 'total')
        )
        serializer_context = {'reserve_map': reserve_map, 'ratings_count_by_customer': ratings_count_by_customer}
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
