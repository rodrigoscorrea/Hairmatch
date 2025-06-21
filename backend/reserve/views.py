from django.shortcuts import render
from datetime import timedelta, datetime, timezone
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
import json
from django.http import JsonResponse
from users.models import User, Customer, Hairdresser
from reserve.models import Reserve
from reserve.serializers import ReserveSerializer, ReserveFullInfoSerializer
from service.models import Service
from agenda.models import Agenda
from availability.models import Availability
import calendar
# Create your views here.


class CreateReserve(APIView):
    def post(self, request):
        data = json.loads(request.body)

        try:
            start_time_iso = data['start_time']
            start_time_dt = timezone.make_aware(datetime.fromisoformat(start_time_iso.replace('Z', '')))
        except (ValueError, KeyError):
             return JsonResponse({'error': 'Invalid or missing start_time. Use ISO format.'}, status=400)
        
        result = create_new_reserve(
            customer_id=data['customer'],
            service_id=data['service'],
            hairdresser_id=data['hairdresser'],
            start_time_dt=start_time_dt
        )

        if 'error' in result:
            return JsonResponse({'error': result['error']}, status=500)
            
        return JsonResponse({'message': 'reserve created successfully'}, status=201)     

class ListReserve(APIView):
    def get(self, request, customer_id=None):
        if(customer_id):
            try:
                customer = Customer.objects.get(id=customer_id)
            except customer.DoesNotExist:
                return JsonResponse({'error': 'Customer not found'}, status=404)
            
            reserves = Reserve.objects.filter(customer=customer_id)
            result = ReserveFullInfoSerializer(reserves, many=True).data
            return JsonResponse({'data': result}, status=200)
            
        reserves = Reserve.objects.all()
        result = ReserveSerializer(reserves, many=True).data 
        return JsonResponse({'data': result}, status=200)   

class UpdateReserve(APIView):
    def put(self, request, reserve_id):
        pass

class RemoveReserve(APIView):
    def delete(self, request, reserve_id):
        try:
            reserve = Reserve.objects.get(id=reserve_id)
        except Reserve.DoesNotExist:
            return JsonResponse({"error": "Result not found"}, status=404)
        

        reserve.delete()
        return JsonResponse({"data": "reserve deleted successfully"}, status=200)
    
class ReserveSlot(APIView):
    def post(self, request, hairdresser_id):
        data = json.loads(request.body)
        service_id = data.get('service')
        date_str = data.get('date')

        if not service_id or not date_str:
            return JsonResponse({'error':'service and date are required'}, status = 400)
        
        result = get_available_slots(hairdresser_id, service_id, date_str)

        if 'error' in result:
            return JsonResponse({'error': result['error']}, status=result.get('status', 400))

        return JsonResponse(result, status=200)
    
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

def generate_time_slots(date, start_time, end_time, bookings, service_duration, break_start=None, break_end=None):
    """Generate available time slots for given date and availability."""
    slots = []
    
    # Convert times to timezone-aware datetime objects
    current_dt = timezone.make_aware(datetime.combine(date, start_time))
    end_dt = timezone.make_aware(datetime.combine(date, end_time))
    
    # Account for service duration
    end_dt = end_dt - timedelta(minutes=service_duration)
    
    # Create 30-minute slots
    slot_duration = timedelta(minutes=30)
    
    # Convert bookings to a list of blocked periods
    blocked_periods = [(b.start_time, b.end_time) for b in bookings]
    
    # Add break time to blocked periods if provided
    if break_start and break_end:
        break_start_dt = timezone.make_aware(datetime.combine(date, break_start))
        break_end_dt = timezone.make_aware(datetime.combine(date, break_end))
        blocked_periods.append((break_start_dt, break_end_dt))
    
    # Generate slots
    while current_dt <= end_dt:
        slot_end = current_dt + timedelta(minutes=service_duration)
        
        # Check if this slot overlaps with any booking or break time
        is_available = True
        for blocked_start, blocked_end in blocked_periods:
            # Check for overlap: if the slot starts before blocked period ends AND
            # slot ends after blocked period starts
            if current_dt < blocked_end and slot_end > blocked_start:
                is_available = False
                break
        
        if is_available:
            slots.append(current_dt.strftime('%H:%M'))
        
        # Move to next slot
        current_dt += slot_duration
    
    return slots

def get_available_slots(hairdresser_id, service_id, date_str):
    try:
        hairdresser = Hairdresser.objects.get(id=hairdresser_id)
        service = Service.objects.get(id=service_id)
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except Hairdresser.DoesNotExist:
        return JsonResponse({'error': 'Hairdresser not found'}, status=404)
    except Service.DoesNotExist:
        return JsonResponse({'error': 'Service not found'}, status=500)
    except ValueError:
        return JsonResponse({'error': 'Invalid date format'}, status=400)
    
    weekday_name = calendar.day_name[selected_date.weekday()]
     
    availability = Availability.objects.filter(
        hairdresser=hairdresser_id,
        weekday=weekday_name.lower()
    ).first()
    
    if not availability:
        return {'available_slots': []}
    
    start_of_day = datetime.combine(selected_date, datetime.min.time())
    end_of_day = datetime.combine(selected_date, datetime.max.time())
    
    bookings = Agenda.objects.filter(
        hairdresser=hairdresser,
        start_time__gte=start_of_day,
        end_time__lte=end_of_day
    ).order_by('start_time')

    # Generate time slots
    available_slots = generate_time_slots(
        selected_date,
        availability.start_time,
        availability.end_time,
        bookings,
        service.duration,
        availability.break_start,  
        availability.break_end
    )

    return {'available_slots' : available_slots}
def create_new_reserve(customer_id, service_id, hairdresser_id, start_time_dt):
    try:
        customer_instace = Customer.objects.get(id=customer_id)
        service_instance = Service.objects.get(id=service_id)
        hairdresser_instance = Hairdresser.objects.get(id=hairdresser_id)

        end_time_dt = start_time_dt + timedelta(minutes=service_instance.duration)

        #checking overlaps
        if Agenda.objects.filter(
            hairdresser= hairdresser_instance,
            start_time__lt=end_time_dt,
            end_time__gt=start_time_dt
        ).exists():
            return {'error':'Desculpe, este horário foi agendado por outra pessoa. Por favor, escolha outro.'}
        
        reserve = Reserve.objects.create(
            start_time = start_time_dt,
            customer=customer_instace,
            service=service_instance
        )
        Agenda.objects.create(
                start_time=start_time_dt,
                end_time=end_time_dt,
                hairdresser=hairdresser_instance,
                service=service_instance
            )
            
        return {'success': True, 'reserve': reserve}
    except (Customer.DoesNotExist, Service.DoesNotExist, Hairdresser.DoesNotExist):
        return {'error': 'Não foi possível encontrar os dados necessários (cliente, serviço ou profissional).'}
    except Exception as e:
        print(f"Error in create_new_reserve: {e}")
        return {'error': 'Ocorreu um erro inesperado ao tentar criar a reserva.'}