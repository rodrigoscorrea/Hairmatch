from django.shortcuts import render
from users.models import User, Hairdresser
from service.models import Service
from service.serializers import ServiceSerializer, ServiceWithHairdresserSerializer
from rest_framework.views import APIView
from django.http import JsonResponse
from agenda.models import Agenda
import json
# Create your views here.

class CreateService(APIView):
    def post(self, request):
        data = json.loads(request.body)
        try:
            hairdresser_instance = Hairdresser.objects.get(id=data['hairdresser'])
        except Hairdresser.DoesNotExist:
            return JsonResponse({'error': 'Hairdresser not found'}, status=500)
        
        if not data.get('name') or not data.get('price') or not data.get('duration'):
            return JsonResponse({'error': 'One of the following required fields is missing: name, price, duration'}, status=400)

        Service.objects.create(
            name=data['name'],
            description=data['description'],
            price=data['price'],
            duration=data['duration'],
            hairdresser=hairdresser_instance,
        )

        return JsonResponse({'message': 'Service created successfully'}, status=201)

class ListService(APIView):
    def get(self, request, service_id=None):
        
        if service_id:
            try:
                service = Service.objects.get(id=service_id)
            except Service.DoesNotExist:
                return JsonResponse({'error': 'Service not found'}, status=404)
            
            result = ServiceSerializer(service).data
            return JsonResponse({'data': result}, status=200)
        
        services = Service.objects.all()
        result = ServiceSerializer(services, many=True).data 
        return JsonResponse({'data': result}, status=200)

class ListServiceHairdresser(APIView):
    def get(self, request, hairdresser_id):
        try:
            hairdresser = Hairdresser.objects.get(id=hairdresser_id)
        except Hairdresser.DoesNotExist:
            return JsonResponse({'error': 'Hairdresser not found'}, status=404)
        
        services = Service.objects.filter(hairdresser=hairdresser)
        services_serialized = ServiceSerializer(services, many=True).data
        return JsonResponse({'data': services_serialized}, status=200)
        
class UpdateService(APIView):
    def put(self, request, service_id):
        data = json.loads(request.body)
        try:
            service = Service.objects.get(id=service_id)
        except Service.DoesNotExist:
            return JsonResponse({"error": "Service not found"}, status=404)
        
        service.name = data['name']
        service.description=data['description']
        service.price=data['price']
        service.duration=data['duration']
        service.save()
        return JsonResponse({'message': 'Service updated successfully'}, status=200)
        
class RemoveService(APIView):
    def delete(self, request, service_id):
        try:
            service_to_delete = Service.objects.get(id=service_id)
            if Agenda.objects.filter(service=service_to_delete).exists():
                return JsonResponse(
                    {"error": "There are already appointments for this service"},
                    status=400
                )
            
            service_to_delete.delete()
            
            return JsonResponse({'message': 'service deleted successfully'}, status=200)

        except Service.DoesNotExist:
            return JsonResponse({"error": "Service not found."}, status=404)
        except Exception as e:
            return JsonResponse({"error": "Unexpected error found."}, status=500)
        