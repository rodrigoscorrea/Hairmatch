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
# Create your views here.

class CreateAgenda(APIView):
    def post(self, request):
        data = json.loads(request.body)

        try:
            # Converter os horários para objetos datetime para manipulação adequada
            start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
        except ValueError:
            return JsonResponse({'error': 'Invalid start_time format'}, status=400)
        
        try:
            hairdresser_instance = Hairdresser.objects.get(id=data['hairdresser'])
        except Hairdresser.DoesNotExist:
            return JsonResponse({'error': 'Hairdresser not found'}, status=500)

        try:
            service_instance = Service.objects.get(id=data['service'])
        except Service.DoesNotExist:
            return JsonResponse({'error': 'Service not found'}, status=500)
        
        # Calcular end_time se não fornecido
        if 'end_time' not in data or not data['end_time']:
            end_time = calculate_end_time(data['start_time'], service_instance.duration)
        else:
            try:
                end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
            except ValueError:
                return JsonResponse({'error': 'Invalid end_time format'}, status=400)
        
        # Verificação completa de sobreposição:
        # Verifica se existem agendamentos que se sobrepõem ao novo agendamento
        overlapping_agendas = Agenda.objects.filter(
            hairdresser=data['hairdresser'],
            # O start_time do agendamento existente é antes do end_time do novo
            start_time__lt=end_time,
            # E o end_time do agendamento existente é depois do start_time do novo
            end_time__gt=start_time
        )
        
        if overlapping_agendas.exists():
            return JsonResponse({
                'error': 'This time slot overlaps with an existing appointment'
            }, status=400)
        
        # Agora é seguro criar o agendamento
        Agenda.objects.create(
            service=service_instance,
            hairdresser=hairdresser_instance,
            start_time=start_time,
            end_time=end_time
        )

        return JsonResponse({'message': 'Agenda register created successfully'}, status=201)

class ListAgenda(APIView):
    def get(self, request, hairdresser_id=None):
        if hairdresser_id:
            try:
                hairdresser = Hairdresser.objects.get(id=hairdresser_id)
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

            except Hairdresser.DoesNotExist:
                return JsonResponse({'error': 'Hairdresser not found'}, status=404)
            
        agendas = Agenda.objects.all()
        result = AgendaSerializer(agendas, many=True).data 
        return JsonResponse({'data': result}, status=200)
    
class UpdateAgenda(APIView):
    def put(self, request, agenda_id):
        pass

class RemoveAgenda(APIView):
    def delete(self, request, agenda_id):
        try:
            agenda = Agenda.objects.get(id=agenda_id)
        except Agenda.DoesNotExist:
            return JsonResponse({"error": "Agenda not found"}, status=404)
        
        agenda.delete()
        return JsonResponse({"data": "Agenda register deleted successfully"}, status=200)
        

def calculate_end_time(start_time, duration_minutes):
    if not isinstance(start_time, str):
        raise TypeError("start_time must be a string")
    
    try:
        # Parse the datetime string - assuming ISO format from JSON
        start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
    except ValueError:
        # If the string doesn't match ISO format, try a more flexible approach
        try:
            start_time = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            raise ValueError("Invalid datetime format. Expected ISO format like '2025-04-26T14:30:00Z'")
    
    if not isinstance(duration_minutes, int):
        try:
            duration_minutes = int(duration_minutes)
        except (ValueError, TypeError):
            raise TypeError("duration_minutes must be an integer")
    
    # Calculate end time by adding the duration in minutes
    end_time = start_time + timedelta(minutes=duration_minutes)
    
    return end_time