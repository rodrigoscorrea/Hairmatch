from django.shortcuts import render
from datetime import timedelta, datetime, timezone
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
import json
import re
from django.http import HttpResponse, JsonResponse
from users.models import User, Customer, Hairdresser
from reserve.models import Reserve
from reserve.serializers import ReserveSerializer, ReserveFullInfoSerializer
from service.models import Service
from agenda.models import Agenda
from availability.models import Availability
import calendar
from django.db import transaction
from django.utils.dateparse import parse_datetime
from hairmatch.problems import body_error, json_object, missing_field_errors, problem_response, query_error, validation_problem
from users.authentication import authenticated_user, authenticated_customer, forbidden
from hairmatch.local_time import LOCAL_TIMEZONE, make_local_aware, local_day_bounds, local_today

# Create your views here.
# What the API answers, in English, and what the WhatsApp chatbot tells the customer, in Portuguese.
CUSTOMER_CONFLICT_DETAIL = 'You already have another reservation at the same time.'
CUSTOMER_CONFLICT_MESSAGE = 'Você já tem outra reserva agendada para o mesmo horário'

def _is_reserve_party(user, reserve):
    """The reserve's customer and the hairdresser who owns its service are the only ones allowed to see or cancel it."""
    return reserve.customer.user_id == user.id or reserve.service.hairdresser.user_id == user.id


def customer_has_conflicting_reserve(customer, start_time, end_time):
    """Whether one of the customer's reserves, with any hairdresser, overlaps [start_time, end_time)."""
    for reservation in Reserve.objects.filter(customer=customer).select_related('service'):
        existing_start = reservation.start_time
        existing_end = calculate_end_time(existing_start, reservation.service.duration)
        if existing_start < end_time and start_time < existing_end:
            return True
    return False


def _integer_field_errors(data, fields):
    """One `errors` item per field of `fields` that is present but not an integer id."""
    errors = []
    for field in fields:
        value = data.get(field)
        if value and (isinstance(value, bool) or not str(value).lstrip('-').isdigit()):
            errors.append(body_error(field, 'This field must be an integer.'))
    return errors


class ReserveById(APIView):
    def get(self, request, id=None):
        session, error = authenticated_user(request)
        if error:
            return error

        try:
            reserve = Reserve.objects.select_related('customer', 'service__hairdresser').get(id=id)
        except Reserve.DoesNotExist:
            return problem_response(request, 'not-found', 'Reservation not found.')
        if not _is_reserve_party(session.user, reserve):
            return forbidden(request)

        result = ReserveFullInfoSerializer(reserve).data
        return JsonResponse({'data': result}, status=200) 


class CreateReserve(APIView):
    def post(self, request):
        # The customer always comes from the session; a `customer` in the body is ignored.
        session, customer_instance, error = authenticated_customer(request)
        if error:
            return error

        data = json_object(request)
        errors = missing_field_errors(data, ['hairdresser', 'service', 'start_time'])
        errors += _integer_field_errors(data, ['hairdresser', 'service'])
        if errors:
            raise validation_problem(errors)

        try:
            hairdresser_instance = Hairdresser.objects.get(id=data['hairdresser'])
            service_instance = Service.objects.get(id=data['service'])
        except Service.DoesNotExist:
            return problem_response(request, 'not-found', 'Service not found.')
        except Hairdresser.DoesNotExist:
            return problem_response(request, 'not-found', 'Hairdresser not found.')

        if service_instance.hairdresser_id != hairdresser_instance.id:
            raise validation_problem([body_error('service', 'The service does not belong to this hairdresser.')])

        try:
            start_time = parse_datetime(data['start_time'])
        except (ValueError, TypeError):
            start_time = None
        if not start_time:
            raise validation_problem([
                body_error('start_time', "The start time must be an ISO 8601 datetime like '2025-04-26T14:30:00Z'.")
            ])

        # The app sends the slot as a naive Manaus time, the clock the slots are listed in.
        start_time = make_local_aware(start_time)

        end_time = calculate_end_time(start_time, service_instance.duration)
        hairdresser_overlap = Agenda.objects.filter(
            hairdresser=hairdresser_instance,
            start_time__lt=end_time,
            end_time__gt=start_time
        ).exists()

        if hairdresser_overlap:
            return problem_response(
                request, 'slot-unavailable', 'The hairdresser is not available during this time slot.'
            )

        if customer_has_conflicting_reserve(customer_instance, start_time, end_time):
            return problem_response(request, 'customer-schedule-conflict', CUSTOMER_CONFLICT_DETAIL)

        # A failure here is unexpected: the transaction rolls back and the central handler answers 500.
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

        return JsonResponse({'message': 'Reserve created successfully'}, status=201)

class ListReserve(APIView):
    def get(self, request, customer_id=None):
        # Only the session customer's own reserves; `/reservations` lists them without the id.
        session, customer, error = authenticated_customer(request)
        if error:
            return error
        if customer_id is not None and customer_id != customer.id:
            return forbidden(request)

        reserves = Reserve.objects.filter(customer=customer).order_by('start_time')
        result = ReserveFullInfoSerializer(reserves, many=True).data
        return JsonResponse({'data': result}, status=200)

class UpdateReserve(APIView):
    def put(self, request, reserve_id):
        pass

class RemoveReserve(APIView):
    def delete(self, request, id):
        session, error = authenticated_user(request)
        if error:
            return error

        try:
            reserve = Reserve.objects.select_related('customer', 'service__hairdresser').get(id=id)
        except Reserve.DoesNotExist:
            return problem_response(request, 'not-found', 'Reservation not found.')
        if not _is_reserve_party(session.user, reserve):
            return forbidden(request)

        reserve.delete()
        return HttpResponse(status=204)
    
class ReserveSlot(APIView):
    def get(self, request, hairdresser_id):
        # A repeated parameter keeps its last value, which is what QueryDict.get returns.
        service_id = request.query_params.get('service')
        date = request.query_params.get('date')
        errors = []
        if not service_id:
            errors.append(query_error('service', 'This field is required.'))
        elif not re.fullmatch(r'-?[0-9]+', service_id):
            errors.append(query_error('service', 'This field must be an integer.'))
        selected_date = None
        if not date:
            errors.append(query_error('date', 'This field is required.'))
        else:
            try:
                selected_date = datetime.strptime(date, '%Y-%m-%d').date()
            except ValueError:
                errors.append(query_error('date', 'The date must be in YYYY-MM-DD format.'))
        if errors:
            raise validation_problem(errors)

        try:
            hairdresser = Hairdresser.objects.get(id=hairdresser_id)
            service = Service.objects.get(id=service_id)
        except Hairdresser.DoesNotExist:
            return problem_response(request, 'not-found', 'Hairdresser not found.')
        except Service.DoesNotExist:
            return problem_response(request, 'not-found', 'Service not found.')

        weekday_name = calendar.day_name[selected_date.weekday()]
        availability = Availability.objects.filter(
            hairdresser=hairdresser,
            weekday=weekday_name.lower()
        ).first()

        if not availability:
            return JsonResponse({'available_slots': []})

        now = timezone.now()
        is_today = (selected_date == local_today())

        start_of_day, end_of_day = local_day_bounds(selected_date)

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
    
    naive_start_dt = datetime.combine(date, start_time)
    naive_end_dt = datetime.combine(date, end_time)

    current_dt = naive_start_dt.replace(tzinfo=LOCAL_TIMEZONE)
    end_dt = naive_end_dt.replace(tzinfo=LOCAL_TIMEZONE)
    
    # The last possible start time must account for the service's duration
    service_delta = timedelta(minutes=service_duration)

    slot_duration = timedelta(minutes=30) 
    last_possible_start_dt = end_dt - service_delta
    # In local time: the loop jumps to a blocked period's end and prints the next slots from there
    blocked_periods = [
        (b.start_time.astimezone(LOCAL_TIMEZONE), b.end_time.astimezone(LOCAL_TIMEZONE)) for b in bookings
    ]
    if break_start and break_end: 
        naive_break_start = datetime.combine(date, break_start)
        naive_break_end = datetime.combine(date, break_end)
        break_start_dt = naive_break_start.replace(tzinfo=LOCAL_TIMEZONE)
        break_end_dt = naive_break_end.replace(tzinfo=LOCAL_TIMEZONE)
        blocked_periods.append((break_start_dt, break_end_dt))

    blocked_periods.sort(key=lambda x: x[0])

    while current_dt <= last_possible_start_dt:
        # Skip slots in the past for today's date
        if now_dt and current_dt < now_dt:
            current_dt += slot_duration
            continue

        slot_end_dt = current_dt + service_delta
 
        is_blocked = False
        for blocked_start, blocked_end in blocked_periods: 
            # Check for overlap 
            if current_dt < blocked_end and slot_end_dt > blocked_start:
                # This slot is blocked.
                is_blocked = True
                # CRITICAL: Jump the clock to the end of the current blockage.
                # This ensures we don't check any more slots within this blocked period.
                current_dt = blocked_end
                break 

        if not is_blocked:
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
        return {'error': 'Service not found', 'status': 404}
    except ValueError:
        return {'error': 'Invalid date format', 'status': 400}

    weekday_name = calendar.day_name[selected_date.weekday()]

    availability = Availability.objects.filter(
        hairdresser=hairdresser,
        weekday=weekday_name.lower()
    ).first()

    if not availability:
        return {'available_slots': []}

    start_of_day, end_of_day = local_day_bounds(selected_date)

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

        if customer_has_conflicting_reserve(customer_instance, start_time_dt, end_time_dt):
            return {'error': CUSTOMER_CONFLICT_MESSAGE}

        with transaction.atomic():
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


class ReservationCollection(ListReserve, CreateReserve):
    """`/api/reservations`: GET lists the logged customer's reservations and POST creates one."""


class ReservationDetail(ReserveById, RemoveReserve):
    """`/api/reservations/{id}`: GET reads and DELETE removes a reservation its party can see."""
