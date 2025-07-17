from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Preferences
from users.models import User
from users.serializers import UserNameSerializer
from .serializers import PreferencesSerializer
from django.http import JsonResponse
import jwt, json

# Create your views here.
class CreatePreferences(APIView):
    def post(self, request):       
        try:
            data = json.loads(request.body)

            preferences = Preferences.objects.create(
                name=data['name'],
                picture=data.get('picture', ''),
            )
            return JsonResponse({'message': "Preferences registered successfully"}, status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
        
class AssignPreferenceToUser(APIView):
    def post(self, request, preference_id):
        token = request.COOKIES.get('jwt')

        if not token:
            return JsonResponse({'error': 'Invalid token'}, status=403)

        try:
            payload = jwt.decode(token, 'secret', algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token expired'}, status=403)
        try:
            user = User.objects.filter(id=payload['id']).first()

            if not user:
                return JsonResponse({'error': 'User not found'}, status=404)

            preference = Preferences.objects.filter(id=preference_id).first()
            if not preference:
                return JsonResponse({'error': 'Preference not found'}, status=404)

            preference.users.add(user)

            return JsonResponse({'message': 'Preference assigned to user successfully'}, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
        
class AssignPreferenceToUserNoCookie(APIView):
    def post(self, request, preference_id):
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')

            if not user_id:
                return JsonResponse({'error': 'User ID is required'}, status=400)

            user = User.objects.filter(id=user_id).first()
            if not user:
                return JsonResponse({'error': 'User not found'}, status=404)

            preference = Preferences.objects.filter(id=preference_id).first()
            if not preference:
                return JsonResponse({'error': 'Preference not found'}, status=404)

            preference.users.add(user)

            return JsonResponse({'message': 'Preference assigned to user successfully'}, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
        
class UnnassignPreferenceFromUser(APIView):
    def post(self, request, preference_id):
        token = request.COOKIES.get('jwt')

        if not token:
            return JsonResponse({'error': 'Invalid token'}, status=403)
        try:
            payload = jwt.decode(token, 'secret', algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token expired'}, status=403)
        try:
            user = User.objects.filter(id=payload['id']).first()

            if not user:
                return JsonResponse({'error': 'User not found'}, status=404)

            preference = Preferences.objects.filter(id=preference_id).first()
            if not preference:
                return JsonResponse({'error': 'Preference not found'}, status=404)

            preference.users.remove(user)

            return JsonResponse({'message': 'Preference unassigned from user successfully'}, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
            

class ListPreferences(APIView):
    def get(self, request, users):
        try:
            preferences = Preferences.objects.filter(users=users)
            if not preferences.exists():
                return Response({'error': 'Preferences not found'}, status=404)
            serializer = PreferencesSerializer(preferences, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=400)
        
class ListAllPreferences(APIView):
    def get(self, request):
        try:
            preferences = Preferences.objects.all()
            serializer = PreferencesSerializer(preferences, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response({'error': str(e)}, status=400)

class ListUsersPerPreference(APIView):
    def get(self, request, preference_id):
        try:
            preference = Preferences.objects.filter(id=preference_id).first()
            if not preference:
                return JsonResponse({'error': 'Preference not found'}, status=404)
            users = preference.users.all()
            serializer = UserNameSerializer(users, many=True)
            return Response({'data':serializer.data},  status=200)
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
            