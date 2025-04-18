from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Availability
from users.models import Hairdresser
from .serializers import AvailabilitySerializer
from django.http import JsonResponse
import jwt, json, datetime
# Create your views here.

class RegisterAvailability(APIView):
    def post(self, request):
        token = request.COOKIES.get('jwt')

        if not token:
            return JsonResponse({'error': 'Invalid token'}, status=403)

        try:
            payload = jwt.decode(token, 'secret', algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token expired'}, status=403)

        try:
            data = json.loads(request.body)

            hairdresser = Hairdresser.objects.filter(user_id=payload['id']).first()
            if not hairdresser:
                return JsonResponse({'error': 'Hairdresser not found'}, status=404)

            if not data.get('weekday') or not data.get('start_time') or not data.get('end_time'):
                return JsonResponse({'error': 'Missing required fields: weekday, start_time, end_time'}, status=400)

            availability = Availability.objects.create(
                weekday=data['weekday'],
                start_time=data['start_time'],
                end_time=data['end_time'],
                hairdresser=hairdresser
            )

            serializer = AvailabilitySerializer(availability)
            return JsonResponse({'message': "Availability registered successfully"}, status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

class ListAvailability(APIView):
    def get(self, request, id):
        try:
            availability = Availability.objects.all().filter(hairdresser_id=id)
            serializer = AvailabilitySerializer(availability, many=True)
            return JsonResponse({'data': serializer.data}, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

class RemoveAvailability(APIView):
    def delete(self, request, id):
        try:
            availability = Availability.objects.get(id=id)
            availability.delete()
            return JsonResponse({'message': 'Availability removed successfully'}, status=200)
        except Availability.DoesNotExist:
            return JsonResponse({'error': 'Availability not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

class UpdateAvailability(APIView):
    def put(self, request, id):
        try:
            availability = Availability.objects.get(id=id)
            data = json.loads(request.body)

            if 'weekday' in data:
                availability.weekday = data['weekday']
            if 'start_time' in data:
                availability.start_time = data['start_time']
            if 'end_time' in data:
                availability.end_time = data['end_time']

            availability.save()
            return JsonResponse({'message': 'Availability updated successfully'}, status=200)
        except Availability.DoesNotExist:
            return JsonResponse({'error': 'Availability not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
