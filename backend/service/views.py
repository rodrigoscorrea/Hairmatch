from django.shortcuts import render
from users.models import User, Hairdresser
from service.models import Service
from service.serializers import ServiceSerializer
from rest_framework.views import APIView
from django.http import JsonResponse
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
            service = Service.objects.get(id=service_id)
        except Service.DoesNotExist:
            return JsonResponse({"error": "Service not found"}, status=404)
        
        service.delete()
        return JsonResponse({"data": "Service register deleted successfully"}, status=200)
        