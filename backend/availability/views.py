from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Availability
from users.models import Hairdresser
from .serializers import AvailabilitySerializer
from django.http import JsonResponse
import jwt, json, datetime
# Create your views here.

class CreateAvailability(APIView):
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

            weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            
            hairdresser = Hairdresser.objects.filter(user_id=payload['id']).first()
            if not hairdresser:
                return JsonResponse({'error': 'Hairdresser not found'}, status=404)

            if not data.get('weekday') or not data.get('start_time') or not data.get('end_time'):
                return JsonResponse({'error': 'One of the following required fields is missing: weekday, start_time, end_time'}, status=400)
            if data['weekday'] not in weekdays:
                return JsonResponse({'error': 'Invalid weekday'}, status=400)
            if Availability.objects.filter(weekday=data['weekday'], hairdresser=hairdresser).exists():
                return JsonResponse({'error': 'Availability already exists'}, status=400)

            if data.get('break_start') and data.get('break_end'):
                availability = Availability.objects.create(
                    weekday=data['weekday'],
                    start_time=data['start_time'],
                    end_time=data['end_time'],
                    break_start=data['break_start'],
                    break_end=data['break_end'],
                    hairdresser=hairdresser
                )
                return JsonResponse({'message': "Availability registered successfully"}, status=201)

            availability = Availability.objects.create(
                    weekday=data['weekday'],
                    start_time=data['start_time'],
                    end_time=data['end_time'],
                    hairdresser=hairdresser
                )

            return JsonResponse({'message': "Availability registered successfully"}, status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

class CreateMultipleAvailability(APIView):
    def post(self, request, hairdresser_id):
        try:
            data = json.loads(request.body)
            availabilities = data['availabilities']
            weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            
            hairdresser = Hairdresser.objects.filter(id=hairdresser_id).first()
            if not hairdresser:
                return JsonResponse({'error': 'Hairdresser not found'}, status=404)

            for availability in availabilities:
                if not availability.get('weekday') or not availability.get('start_time') or not availability.get('end_time'):
                    return JsonResponse({'error': 'One of the following required fields is missing: weekday, start_time, end_time'}, status=400)
                if availability['weekday'] not in weekdays:
                    return JsonResponse({'error': 'Invalid weekday'}, status=400)
                if Availability.objects.filter(weekday=availability['weekday'], hairdresser=hairdresser).exists():
                    return JsonResponse({'error': 'Availability already exists'}, status=400)

                if availability.get('break_start') and availability.get('break_end'):
                    Availability.objects.create(
                        weekday=availability['weekday'],
                        start_time=availability['start_time'],
                        end_time=availability['end_time'],
                        break_start=availability['break_start'],
                        break_end=availability['break_end'],
                        hairdresser=hairdresser
                    )
                else:
                    Availability.objects.create(
                        weekday=availability['weekday'],
                        start_time=availability['start_time'],
                        end_time=availability['end_time'],
                        hairdresser=hairdresser
                    )

            return JsonResponse({'message': "Multiple availabilities registered successfully"}, status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

class ListAvailability(APIView):
    def get(self, request, hairdresser_id):
        result = get_hairdresser_availability(hairdresser_id)

        if 'error' in result:
            return JsonResponse(result, status=result.get('status',400))
        
        serialized_data = result['availabilities']
        working_days = [avail['weekday'].lower() for avail in serialized_data]
            
        # Convert to numerical representation (days the hairdresser does NOT work)
        non_working_day_numbers = self.get_non_working_days(working_days)
        
        response_data = {
            'data': serialized_data,
            'non_working_days': non_working_day_numbers
        }
        
        return JsonResponse(response_data, status=200)
    
    def get_non_working_days(self, working_days):
        """
        Convert nominal weekdays to their numerical representation (0-6)
        and return the days the hairdresser doesn't work
        
        Args:
            working_days: List of weekday names that the hairdresser works
            
        Returns:
            List of integers representing days the hairdresser does NOT work (0=Sunday, 1=Monday, etc.)
        """
        weekday_map = {
            'sunday': 0,
            'monday': 1,
            'tuesday': 2,
            'wednesday': 3,
            'thursday': 4,
            'friday': 5,
            'saturday': 6
        }
        
        # Get all days the hairdresser doesn't work
        all_days = set(range(7))  # 0-6
        working_day_numbers = set(weekday_map.get(day.lower(), -1) for day in working_days)
        
        # Remove invalid mappings if any
        working_day_numbers.discard(-1)
        
        # Return days the hairdresser doesn't work
        return list(all_days - working_day_numbers)

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

class UpdateMultipleAvailability(APIView):
    def put(self, request, hairdresser_id):
        try:
            data = json.loads(request.body)
            availabilities = data['availabilities']
            weekdays = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            
            hairdresser = Hairdresser.objects.filter(id=hairdresser_id).first()
            if not hairdresser:
                return JsonResponse({'error': 'Hairdresser not found'}, status=404)

            are_availabilities_deleted = delete_all_availabilities_by_hairdresser_safe(hairdresser_id)
            if not are_availabilities_deleted:
                return JsonResponse({'error': 'Unable to delete hairdresser availabilities'}, status=500)
            
            for availability in availabilities:
                if not availability.get('weekday') or not availability.get('start_time') or not availability.get('end_time'):
                    return JsonResponse({'error': 'One of the following required fields is missing: weekday, start_time, end_time'}, status=400)
                if availability['weekday'] not in weekdays:
                    return JsonResponse({'error': 'Invalid weekday'}, status=400)
                if Availability.objects.filter(weekday=availability['weekday'], hairdresser=hairdresser).exists():
                    return JsonResponse({'error': 'Availability already exists'}, status=400)

                if availability.get('break_start') and availability.get('break_end'):
                    Availability.objects.create(
                        weekday=availability['weekday'],
                        start_time=availability['start_time'],
                        end_time=availability['end_time'],
                        break_start=availability['break_start'],
                        break_end=availability['break_end'],
                        hairdresser=hairdresser
                    )
                else:
                    Availability.objects.create(
                        weekday=availability['weekday'],
                        start_time=availability['start_time'],
                        end_time=availability['end_time'],
                        hairdresser=hairdresser
                    )

            return JsonResponse({'message': "Multiple availabilities registered successfully"}, status=201)
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


def delete_all_availabilities_by_hairdresser_safe(hairdresser_id: int) -> bool:
    try:
        deleted_count, _ = Availability.objects.filter(hairdresser=hairdresser_id).delete()
        return True
    except Exception as e:
        return False
    
def get_hairdresser_availability(hairdresser_id):
    try:
        if not Hairdresser.objects.filter(id=hairdresser_id).exists:
            return {'error' : 'Hairdresser not found', 'status':'404'}
        availabilities = Availability.objects.filter(hairdresser_id=hairdresser_id)
        weekday_order = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
        sorted_availabilities = sorted(availabilities, key=lambda a: weekday_order.index(a.weekday.lower()))

        serializer = AvailabilitySerializer(sorted_availabilities, many=True)
        return {'availabilities': serializer.data}
    except Exception as e:
        return {'error': str(e), 'status': 400}   