from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Preferences
from users.models import User
from .serializers import PreferencesSerializer
from django.http import JsonResponse
import jwt, json

# Create your views here.
class CreatePreferences(APIView):
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

            user = User.objects.filter(id=payload['id']).first()
            if not user:
                return JsonResponse({'error': 'User not found'}, status=404)

            preferences = Preferences.objects.create(
                name=data['name'],
                picture=data.get('picture', ''),
            )
            preferences.user_id.set([user])  # Set the user for the preferences
            return JsonResponse({'message': "Preferences registered successfully"}, status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

class ListPreferences(APIView):
    def get(self, request, user_id):
        try:
            preferences = Preferences.objects.filter(user_id=user_id)
            serializer = PreferencesSerializer(preferences, many=True)
            return Response(serializer.data)
            if not preferences.exists():
                return Response({'error': 'Preferences not found'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=400)

class UpdatePreferences(APIView):
    def put(self, request, id): # Preference ID
        try:
            data = json.loads(request.body)
            preference = Preferences.objects.filter(id=id).first()
            if not preference:
                return JsonResponse({'error': 'Preference not found'}, status=404)
            if 'name' in data:
                preference.name = data['name']
            if 'picture' in data:
                preference.picture = data['picture']
            preference.save()
            return JsonResponse({'message': 'Preference updated successfully'}, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


            

class RemovePreferences(APIView):
    def delete(self, request, id): # Preference ID
        try:
            preference = Preferences.objects.filter(id=id).first()
            if not preference:
                return JsonResponse({'error': 'Preference not found'}, status=404)
            preference.delete()
            return JsonResponse({'message': 'Preference removed successfully'}, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
            