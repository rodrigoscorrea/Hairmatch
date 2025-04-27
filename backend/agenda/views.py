from django.shortcuts import render
from agenda.models import Agenda
from agenda.serializers import AgendaSerializer
from users.models import User, Hairdresser
from service.models import Service
from rest_framework.views import APIView
from django.http import JsonResponse
import json
# Create your views here.

class CreateAgenda(APIView):
    def post(self, request):
        data = json.loads(request.body)
        try:
            hairdresser_instance = Hairdresser.objects.get(id=data['hairdresser'])
        except Hairdresser.DoesNotExist:
            return JsonResponse({'error': 'Hairdresser not found'}, status=500)

        try:
            service_instance = Service.objects.get(id=data['service'])
        except Service.DoesNotExist:
            return JsonResponse({'error': 'Service not found'}, status=500)
        
        Agenda.objects.create(
            service=service_instance,
            hairdresser=hairdresser_instance,
            start_time = data['start_time'],
            end_time = data['end_time']
        )

        return JsonResponse({'message': 'Agenda register created successfully'}, status=201)

class ListAgenda(APIView):
    def get(self, request, hairdresser_id=None):
        
        if hairdresser_id:
            try:
                hairdresser = Hairdresser.objects.get(id=hairdresser_id)
            except Hairdresser.DoesNotExist:
                return JsonResponse({'error': 'Hairdresser not found'}, status=404)
            hairdresser_agendas = Agenda.objects.filter(hairdresser=hairdresser_id)
            result = AgendaSerializer(hairdresser_agendas, many=True).data
            return JsonResponse({'data': result}, status=200)
        
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
        