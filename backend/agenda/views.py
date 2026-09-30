from django.shortcuts import render
from agenda.models import Agenda
from agenda.serializers import AgendaSerializer
from users.models import User, Hairdresser
from service.models import Service
from rest_framework.views import APIView
from django.http import JsonResponse
import json
from datetime import timedelta, datetime
from reserve.models import Reserve
from django.db.models import Q
from users.authentication import authenticated_hairdresser, forbidden
from hairmatch.local_time import make_local_aware
# Create your views here.

class CreateAgenda(APIView):
    def post(self, request):
        # Blocks a slot in the session hairdresser's own agenda; a `hairdresser` in the body is ignored.
        session, hairdresser_instance, error = authenticated_hairdresser(request)
        if error:
            return error

        try:
            data = json.loads(request.body)
            # Convert the schedule times to datetime objects for proper handling
            start_time = make_local_aware(datetime.fromisoformat(data['start_time'].replace('Z', '+00:00')))
        except (ValueError, KeyError, TypeError, AttributeError):
            return JsonResponse({'error': 'Invalid start_time format'}, status=400)

        try:
            service_instance = Service.objects.get(id=data.get('service'))
        except (Service.DoesNotExist, ValueError, TypeError):
            return JsonResponse({'error': 'Service not found'}, status=500)
        if service_instance.hairdresser_id != hairdresser_instance.id:
            return forbidden()
        
        # Calculate end_time if not provided
        if 'end_time' not in data or not data['end_time']:
            end_time = start_time + timedelta(minutes=service_instance.duration)
        else:
            try:
                end_time = make_local_aware(datetime.fromisoformat(data['end_time'].replace('Z', '+00:00')))
            except (ValueError, TypeError, AttributeError):
                return JsonResponse({'error': 'Invalid end_time format'}, status=400)
        
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
            return JsonResponse({
                'error': 'This time slot overlaps with an existing appointment'
            }, status=400)

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
            return forbidden()

        agenda_items = Agenda.objects.filter(hairdresser=hairdresser).select_related('service')
        if not agenda_items.exists():
            return JsonResponse({'data': []}, status=200)
        reserve_identifiers = set()
        for item in agenda_items:
            reserve_identifiers.add((item.service_id, item.start_time))

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
            return JsonResponse({"error": "Agenda not found"}, status=404)
        if agenda.hairdresser_id != hairdresser.id:
            return forbidden()

        agenda.delete()
        return JsonResponse({"data": "Agenda register deleted successfully"}, status=200)
