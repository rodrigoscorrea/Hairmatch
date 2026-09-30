import logging

from django.http import HttpResponse, JsonResponse
from django.utils.dateparse import parse_time
from rest_framework.views import APIView

from hairmatch.problems import Problem, body_error, json_object, problem_response, validation_problem
from users.authentication import authenticated_hairdresser, forbidden
from users.models import Hairdresser

from .models import Availability
from .serializers import AvailabilitySerializer

logger = logging.getLogger(__name__)

WEEKDAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
REQUIRED_FIELDS = ['weekday', 'start_time', 'end_time']
TIME_FIELDS = ['start_time', 'end_time', 'break_start', 'break_end']
AVAILABILITY_EXISTS_DETAIL = 'An availability already exists for this weekday.'


def _is_time(value):
    """Whether `value` is a time of day in HH:MM or HH:MM:SS."""
    try:
        return isinstance(value, str) and parse_time(value) is not None
    except ValueError:
        return False


def _availability_errors(item, prefix='', partial=False):
    """
    `errors` items for one availability dict: a required field that is missing, a weekday
    outside the week and a time that is not HH:MM. With `partial`, only the fields present are checked.
    `prefix` is the JSON Pointer of the item inside a bulk body (`availabilities/0/`).
    """
    errors = []
    for field in REQUIRED_FIELDS:
        if not partial and not item.get(field):
            errors.append(body_error(f'{prefix}{field}', 'This field is required.'))
    if item.get('weekday') and item['weekday'] not in WEEKDAYS:
        errors.append(body_error(f'{prefix}weekday', 'The weekday must be one of monday to sunday.'))
    for field in TIME_FIELDS:
        value = item.get(field)
        if value and not _is_time(value):
            errors.append(body_error(f'{prefix}{field}', 'The time must be in HH:MM format.'))
    return errors


def _bulk_items(data):
    """
    The `availabilities` list of a bulk body. Raises a validation Problem, before anything is written,
    when it is missing, is not a list of objects or has an invalid item.
    """
    items = data.get('availabilities')
    if items is None:
        raise validation_problem([body_error('availabilities', 'This field is required.')])
    if not isinstance(items, list):
        raise validation_problem([body_error('availabilities', 'This field must be a list.')])
    errors = []
    for index, item in enumerate(items):
        if isinstance(item, dict):
            errors += _availability_errors(item, prefix=f'availabilities/{index}/')
        else:
            errors.append(body_error(f'availabilities/{index}', 'Each item must be an object.'))
    if errors:
        raise validation_problem(errors)
    return items


def _create_availability(hairdresser, item):
    fields = {
        'weekday': item['weekday'],
        'start_time': item['start_time'],
        'end_time': item['end_time'],
        'hairdresser': hairdresser,
    }
    if item.get('break_start') and item.get('break_end'):
        fields['break_start'] = item['break_start']
        fields['break_end'] = item['break_end']
    return Availability.objects.create(**fields)


def _create_from_bulk(request, hairdresser, items):
    """Creates the items one by one, as before: it stops at the first weekday that already exists."""
    for item in items:
        if Availability.objects.filter(weekday=item['weekday'], hairdresser=hairdresser).exists():
            return problem_response(request, 'availability-exists', AVAILABILITY_EXISTS_DETAIL)
        _create_availability(hairdresser, item)
    return None


class CreateAvailability(APIView):
    def post(self, request):
        session, hairdresser, error = authenticated_hairdresser(request)
        if error:
            return error

        data = json_object(request)
        errors = _availability_errors(data)
        if errors:
            raise validation_problem(errors)
        if Availability.objects.filter(weekday=data['weekday'], hairdresser=hairdresser).exists():
            return problem_response(request, 'availability-exists', AVAILABILITY_EXISTS_DETAIL)

        _create_availability(hairdresser, data)
        return JsonResponse({'message': "Availability registered successfully"}, status=201)

class CreateMultipleAvailability(APIView):
    def post(self, request, hairdresser_id):
        # The hairdresser comes from the session; the id in the URL must be the session's.
        session, hairdresser, error = authenticated_hairdresser(request)
        if error:
            return error
        if hairdresser_id != hairdresser.id:
            return forbidden(request)

        items = _bulk_items(json_object(request))
        failure = _create_from_bulk(request, hairdresser, items)
        if failure:
            return failure

        return JsonResponse({'message': "Multiple availabilities registered successfully"}, status=201)

class ListAvailability(APIView):
    def get(self, request, hairdresser_id):
        if not Hairdresser.objects.filter(id=hairdresser_id).exists():
            return problem_response(request, 'not-found', 'Hairdresser not found.')
        result = get_hairdresser_availability(hairdresser_id)
        if 'error' in result:
            # Only reached when reading the availabilities failed; the helper logged why.
            logger.error('Listing the availabilities of hairdresser %s failed', hairdresser_id)
            return problem_response(request, 'internal-error', 'The availabilities could not be listed.')

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
        session, hairdresser, error = authenticated_hairdresser(request)
        if error:
            return error

        try:
            availability = Availability.objects.get(id=id)
        except Availability.DoesNotExist:
            return problem_response(request, 'not-found', 'Availability not found.')
        if availability.hairdresser_id != hairdresser.id:
            return forbidden(request)
        availability.delete()
        return HttpResponse(status=204)

class UpdateMultipleAvailability(APIView):
    def put(self, request, hairdresser_id):
        # Replaces the whole work schedule, so only its owner can call it.
        session, hairdresser, error = authenticated_hairdresser(request)
        if error:
            return error
        if hairdresser_id != hairdresser.id:
            return forbidden(request)

        items = _bulk_items(json_object(request))

        are_availabilities_deleted = delete_all_availabilities_by_hairdresser_safe(hairdresser.id)
        if not are_availabilities_deleted:
            raise Problem('internal-error', 'The current availabilities could not be replaced.')

        failure = _create_from_bulk(request, hairdresser, items)
        if failure:
            return failure

        return JsonResponse({'message': "Multiple availabilities registered successfully"}, status=200)

class UpdateAvailability(APIView):
    def patch(self, request, id):
        session, hairdresser, error = authenticated_hairdresser(request)
        if error:
            return error

        try:
            availability = Availability.objects.get(id=id)
        except Availability.DoesNotExist:
            return problem_response(request, 'not-found', 'Availability not found.')
        if availability.hairdresser_id != hairdresser.id:
            return forbidden(request)

        data = json_object(request)
        errors = _availability_errors(data, partial=True)
        if errors:
            raise validation_problem(errors)

        if 'weekday' in data:
            availability.weekday = data['weekday']
        if 'start_time' in data:
            availability.start_time = data['start_time']
        if 'end_time' in data:
            availability.end_time = data['end_time']

        availability.save()
        return JsonResponse({'message': 'Availability updated successfully'}, status=200)


def delete_all_availabilities_by_hairdresser_safe(hairdresser_id: int) -> bool:
    try:
        deleted_count, _ = Availability.objects.filter(hairdresser=hairdresser_id).delete()
        return True
    except Exception as e:
        return False
    
def get_hairdresser_availability(hairdresser_id):
    try:
        if not Hairdresser.objects.filter(id=hairdresser_id).exists():
            return {'error' : 'Hairdresser not found', 'status':'404'}
        availabilities = Availability.objects.filter(hairdresser_id=hairdresser_id)
        weekday_order = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
        sorted_availabilities = sorted(availabilities, key=lambda a: weekday_order.index(a.weekday.lower()))

        serializer = AvailabilitySerializer(sorted_availabilities, many=True)
        return {'availabilities': serializer.data}
    except Exception:
        logger.exception('Reading the availabilities of hairdresser %s failed', hairdresser_id)
        return {'error': 'The availabilities could not be read.', 'status': 500}   

class HairdresserAvailabilities(ListAvailability, CreateMultipleAvailability, UpdateMultipleAvailability):
    """`/api/hairdressers/{id}/availabilities`: GET reads, POST adds to and PUT replaces the work schedule."""


class AvailabilityDetail(UpdateAvailability, RemoveAvailability):
    """`/api/availabilities/{id}`: PATCH updates and DELETE removes one availability."""
