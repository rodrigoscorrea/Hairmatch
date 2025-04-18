from django.http import JsonResponse
from rest_framework.views import APIView
from .models import Preferences
from .serializers import PreferencesSerializer
import json
import jwt

# Views relacionadas às preferências do usuário

class RegisterPreference(APIView):
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

            if 'name' not in data:
                return JsonResponse({'error': 'Missing required fields: name'}, status=400)

            preference = Preferences.objects.create(
                name=data['name'],
                picture=data['picture'],
                user_id=payload['id']
            )

            serializer = PreferencesSerializer(preference)
            return JsonResponse({'message': serializer.data}, status=201)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


class ListPreferences(APIView):
    def get(self, request):
        token = request.COOKIES.get('jwt')

        if not token:
            return JsonResponse({'error': 'Invalid token'}, status=403)

        try:
            payload = jwt.decode(token, 'secret', algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token expired'}, status=403)

        try:
            preferences = Preferences.objects.filter(user_id=payload['id'])
            serializer = PreferencesSerializer(preferences, many=True)
            return JsonResponse({'data':serializer.data}, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

class ListPreferencesNoCookie(APIView):
    def get(self, request, id):
        try:
            preferences = Preferences.objects.filter(user_id=id)
            serializer = PreferencesSerializer(preferences, many=True)
            return JsonResponse({'data':serializer.data}, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

class RemovePreference(APIView):
    def delete(self, request, id):
        token = request.COOKIES.get('jwt')

        if not token:
            return JsonResponse({'error': 'Invalid token'}, status=403)

        try:
            payload = jwt.decode(token, 'secret', algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token expired'}, status=403)

        try:
            preference = Preferences.objects.get(id=id, user_id=payload['id'])
            preference.delete()
            return JsonResponse({'message': 'Preference deleted successfully'}, status=200)

        except Preferences.DoesNotExist:
            return JsonResponse({'error': 'Preference not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

class UpdatePreference(APIView):
    def put(self, request, id):
        token = request.COOKIES.get('jwt')

        if not token:
            return JsonResponse({'error': 'Invalid token'}, status=403)

        try:
            payload = jwt.decode(token, 'secret', algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token expired'}, status=403)

        try:
            preference = Preferences.objects.get(id=id, user_id=payload['id'])
            data = json.loads(request.body)

            # Atualiza apenas os campos fornecidos
            if 'name' in data:
                preference.name = data['name']
            if 'picture' in data:
                preference.picture = data['picture']

            preference.save()

            serializer = PreferencesSerializer(preference)
            return JsonResponse(serializer.data, status=200)

        except Preferences.DoesNotExist:
            return JsonResponse({'error': 'Preference not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
