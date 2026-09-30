from decimal import Decimal, InvalidOperation

from django.http import HttpResponse, JsonResponse
from rest_framework.views import APIView

from agenda.models import Agenda
from hairmatch.problems import body_error, json_object, missing_field_errors, problem_response, validation_problem
from service.models import Service
from service.serializers import ServiceSerializer, ServiceWithHairdresserSerializer
from users.authentication import authenticated_hairdresser, forbidden
from users.models import User, Hairdresser

SERVICE_REQUIRED_FIELDS = ['name', 'price', 'duration']


def _service_errors(data):
    """`errors` items for a service body: name, price and duration are required, price a number and duration whole minutes."""
    errors = missing_field_errors(data, SERVICE_REQUIRED_FIELDS)
    if data.get('price'):
        try:
            Decimal(str(data['price']))
        except InvalidOperation:
            errors.append(body_error('price', 'This field must be a number.'))
    duration = data.get('duration')
    if duration and (isinstance(duration, bool) or not str(duration).isdigit()):
        errors.append(body_error('duration', 'This field must be a whole number of minutes.'))
    return errors


class CreateService(APIView):
    def post(self, request):
        # The service always belongs to the session hairdresser; a `hairdresser` in the body is ignored.
        session, hairdresser_instance, error = authenticated_hairdresser(request)
        if error:
            return error

        data = json_object(request)
        errors = _service_errors(data)
        if errors:
            raise validation_problem(errors)

        Service.objects.create(
            name=data['name'],
            description=data.get('description', ''),
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
                return problem_response(request, 'not-found', 'Service not found.')
            
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
            return problem_response(request, 'not-found', 'Hairdresser not found.')
        
        services = Service.objects.filter(hairdresser=hairdresser)
        services_serialized = ServiceSerializer(services, many=True).data
        return JsonResponse({'data': services_serialized}, status=200)
        
class UpdateService(APIView):
    def put(self, request, service_id):
        session, hairdresser, error = authenticated_hairdresser(request)
        if error:
            return error

        try:
            service = Service.objects.get(id=service_id)
        except Service.DoesNotExist:
            return problem_response(request, 'not-found', 'Service not found.')
        if service.hairdresser_id != hairdresser.id:
            return forbidden(request)

        data = json_object(request)
        errors = _service_errors(data)
        if errors:
            raise validation_problem(errors)

        service.name = data['name']
        service.description=data.get('description', service.description)
        service.price=data['price']
        service.duration=data['duration']
        service.save()
        return JsonResponse({'message': 'Service updated successfully'}, status=200)
        
class RemoveService(APIView):
    def delete(self, request, service_id):
        session, hairdresser, error = authenticated_hairdresser(request)
        if error:
            return error

        try:
            service_to_delete = Service.objects.get(id=service_id)
        except Service.DoesNotExist:
            return problem_response(request, 'not-found', 'Service not found.')
        if service_to_delete.hairdresser_id != hairdresser.id:
            return forbidden(request)
        if Agenda.objects.filter(service=service_to_delete).exists():
            return problem_response(
                request, 'service-has-reservations', 'This service has reservations and cannot be deleted.'
            )

        service_to_delete.delete()
        return HttpResponse(status=204)
