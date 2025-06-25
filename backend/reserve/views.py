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
from django.db import transaction
from rest_framework import status
from django.utils.dateparse import parse_datetime
# Create your views here.

class ReserveById(APIView):
    def get(self, request, id=None):
    
        try:
            reserve = Reserve.objects.get(id=id)
        except Reserve.DoesNotExist:
            return JsonResponse({'error': 'Reserve not found'}, status=404)
        
        result = ReserveFullInfoSerializer(reserve).data
        return JsonResponse({'data': result}, status=200) 


class CreateReserve(APIView):
    def post(self, request):
        try:
            data = json.loads(request.body)
            customer_id = data['customer']
            hairdresser_id = data['hairdresser']
            service_id = data['service']
            start_time_str = data['start_time']
        except (json.JSONDecodeError, KeyError) as e:
            return JsonResponse({'error': f'Invalid request body: {e}'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            customer_instance = Customer.objects.get(id=customer_id)
            hairdresser_instance = Hairdresser.objects.get(id=hairdresser_id)
            service_instance = Service.objects.get(id=service_id)
        except Customer.DoesNotExist:
            return JsonResponse({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)
        except Service.DoesNotExist:
            return JsonResponse({'error': 'Service not found'}, status=status.HTTP_404_NOT_FOUND)
        except Hairdresser.DoesNotExist:
            return JsonResponse({'error': 'Hairdresser not found'}, status=status.HTTP_404_NOT_FOUND)

        start_time = parse_datetime(start_time_str)
        if not start_time:
            return JsonResponse(
                {'error': "Invalid datetime format. Expected ISO format like '2025-04-26T14:30:00Z'"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if timezone.is_naive(start_time):
             start_time = timezone.make_aware(start_time)

        end_time = calculate_end_time(start_time, service_instance.duration)
        hairdresser_overlap = Agenda.objects.filter(
            hairdresser=hairdresser_instance,
            start_time__lt=end_time,
            end_time__gt=start_time
        ).exists()

        if hairdresser_overlap:
            return JsonResponse(
                {'error': 'The hairdresser is not available during this time slot.'},
                status=status.HTTP_409_CONFLICT
            )

        customer_reservations = Reserve.objects.filter(customer=customer_instance).select_related('service')
        for reservation in customer_reservations:
            existing_start = reservation.start_time

            if timezone.is_naive(existing_start):
                existing_start = timezone.make_aware(existing_start)
            
            existing_end = calculate_end_time(existing_start, reservation.service.duration)
            
            if existing_start < end_time and start_time < existing_end:
                 return JsonResponse(
                     {'error': 'Você já tem outra reserva agendada para o mesmo horário'},
                     status=status.HTTP_409_CONFLICT
                 )

        try:
            with transaction.atomic():
                Reserve.objects.create(
                    start_time=start_time,
                    customer=customer_instance,
                    service=service_instance,
                )
                
                Agenda.objects.create(
                    start_time=start_time,
                    end_time=end_time,
                    hairdresser=hairdresser_instance,
                    service=service_instance
                )
        except Exception as e:
            return JsonResponse(
                {'error': f'An error occurred while saving the reservation: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        return JsonResponse({'message': 'Reserve created successfully'}, status=status.HTTP_201_CREATED)     

class ListReserve(APIView):
    def get(self, request, customer_id=None):
        if(customer_id):
            try:
                customer = Customer.objects.get(id=customer_id)
            except customer.DoesNotExist:
                return JsonResponse({'error': 'Customer not found'}, status=404)
            
            reserves = Reserve.objects.filter(customer=customer_id).order_by('start_time')
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
        try:
            data = json.loads(request.body)
            service_id = data['service']
            date_str = data['date']
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except (json.JSONDecodeError, KeyError):
            return JsonResponse({'error': 'Invalid payload. "service" and "date" are required.'}, status=400)
        except ValueError:
            return JsonResponse({'error': 'Invalid date format. Please use YYYY-MM-DD.'}, status=400)

        try:
            hairdresser = Hairdresser.objects.get(id=hairdresser_id)
            service = Service.objects.get(id=service_id)
        except Hairdresser.DoesNotExist:
            return JsonResponse({'error': 'Hairdresser not found'}, status=404)
        except Service.DoesNotExist:
            return JsonResponse({'error': 'Service not found'}, status=404)

        weekday_name = calendar.day_name[selected_date.weekday()]
        availability = Availability.objects.filter(
            hairdresser=hairdresser,
            weekday=weekday_name.lower()
        ).first()

        if not availability:
            return JsonResponse({'available_slots': []})

        now = timezone.now()
        is_today = (selected_date == now.date())

        start_of_day = timezone.make_aware(datetime.combine(selected_date, datetime.min.time()))
        end_of_day = timezone.make_aware(datetime.combine(selected_date, datetime.max.time()))

        bookings = Agenda.objects.filter(
            hairdresser=hairdresser,
            start_time__lt=end_of_day,
            end_time__gt=start_of_day
        ).order_by('start_time')

        available_slots = generate_time_slots(
            selected_date,
            availability.start_time,
            availability.end_time,
            bookings,
            service.duration,
            availability.break_start,
            availability.break_end,

            now_dt=now if is_today else None
        )

        return JsonResponse({'available_slots': available_slots})
    
def calculate_end_time(start_dt: datetime, duration_minutes: int) -> datetime:
    """
    Calculates the end time by adding a duration in minutes to a start datetime.
    
    Args:
        start_dt: A datetime object representing the start time.
        duration_minutes: An integer representing the duration in minutes.
        
    Returns:
        A datetime object representing the end time.
    
    Raises:
        TypeError: If the input types are incorrect.
    """
    if not isinstance(start_dt, datetime):
        raise TypeError("start_dt must be a datetime object")
    
    try:
        duration = int(duration_minutes)
    except (ValueError, TypeError):
        raise TypeError("duration_minutes must be convertible to an integer.")
        
    return start_dt + timedelta(minutes=duration)

def generate_time_slots(date, start_time, end_time, bookings, service_duration, 
                        break_start=None, break_end=None, now_dt=None):
    """
    Generate available time slots for a given date and availability.
    If now_dt is provided, it will filter out slots that are in the past.
    """
    slots = []
    
    # Convert start/end times to timezone-aware datetime objects for today's date
    current_dt = timezone.make_aware(datetime.combine(date, start_time))
    end_dt = timezone.make_aware(datetime.combine(date, end_time))
    
    # The last possible start time must account for the service's duration
    end_dt -= timedelta(minutes=service_duration)
    
    slot_duration = timedelta(minutes=30)
    
    # Convert bookings to a list of blocked periods for easy checking
    blocked_periods = [(b.start_time, b.end_time) for b in bookings]
    
    if break_start and break_end:
        break_start_dt = timezone.make_aware(datetime.combine(date, break_start))
        break_end_dt = timezone.make_aware(datetime.combine(date, break_end))
        blocked_periods.append((break_start_dt, break_end_dt))
    
    # --- Main Loop to Generate Slots ---
    while current_dt <= end_dt:
        # ** NEW LOGIC: If checking for today, skip slots that are already in the past **
        if now_dt and current_dt <= now_dt:
            current_dt += slot_duration
            continue  # Skip to the next potential slot

        slot_end = current_dt + timedelta(minutes=service_duration)
        
        is_available = True
        for blocked_start, blocked_end in blocked_periods:
            # Check for any overlap between the potential slot and a blocked period
            if current_dt < blocked_end and slot_end > blocked_start:
                is_available = False
                break
        
        if is_available:
            slots.append(current_dt.strftime('%H:%M'))
        
        current_dt += slot_duration
    
    return slots

def get_available_slots(hairdresser_id, service_id, date_str):
    try:
        hairdresser = Hairdresser.objects.get(id=hairdresser_id)
        service = Service.objects.get(id=service_id)
        selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except Hairdresser.DoesNotExist:
        return {'error': 'Hairdresser not found', 'status': 404}
    except Service.DoesNotExist:
        return {'error': 'Service not found', 'status': 500}
    except ValueError:
        return {'error': 'Invalid date format', 'status': 400}

    weekday_name = calendar.day_name[selected_date.weekday()]

    availability = Availability.objects.filter(
        hairdresser=hairdresser,
        weekday=weekday_name.lower()
    ).first()

    if not availability:
        return {'available_slots': []}

    start_of_day = timezone.make_aware(datetime.combine(selected_date, datetime.min.time()))
    end_of_day = timezone.make_aware(datetime.combine(selected_date, datetime.max.time()))

    bookings = Agenda.objects.filter(
        hairdresser=hairdresser,
        start_time__lt=end_of_day,
        end_time__gt=start_of_day
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
        customer_instance = Customer.objects.get(id=customer_id)
        service_instance = Service.objects.get(id=service_id)
        hairdresser_instance = Hairdresser.objects.get(id=hairdresser_id)

        end_time_dt = start_time_dt + timedelta(minutes=service_instance.duration)

        # Checking for overlapping appointments in the Agenda
        if Agenda.objects.filter(
            hairdresser=hairdresser_instance,
            start_time__lt=end_time_dt,
            end_time__gt=start_time_dt
        ).exists():
            return {'error': 'Desculpe, este horário foi agendado por outra pessoa. Por favor, escolha outro.'}
        
        reserve = Reserve.objects.create(
            start_time=start_time_dt,
            customer=customer_instance,
            service=service_instance
        )
        Agenda.objects.create(
            start_time=start_time_dt,
            end_time=end_time_dt,
            hairdresser=hairdresser_instance,
            service=service_instance
        )
            
        return {'success': True, 'reserve': reserve}
    except Customer.DoesNotExist:
        return {'error': 'Customer not found'}
    except Service.DoesNotExist:
        return {'error': 'Service not found'}
    except Hairdresser.DoesNotExist:
        return {'error': 'Hairdresser not found'}
    except Exception as e:
        # Catch any other unexpected errors
        print(f"An unexpected error occurred in create_new_reserve: {e}")
        return {'error': 'Ocorreu um erro inesperado ao tentar criar a reserva.'}