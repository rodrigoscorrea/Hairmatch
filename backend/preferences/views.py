from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Preferences
from users.models import User
from users.serializers import UserNameSerializer
from .serializers import PreferencesSerializer
from django.http import JsonResponse
import json
from users.authentication import authenticated_user

# Create your views here.
# The catalog comes from the populate_preferences seed; the API does not create, edit or remove it.
class AssignPreferenceToUser(APIView):
    def post(self, request, preference_id):
        session, error = authenticated_user(request)
        if error:
            return error
        try:
            user = session.user

            preference = Preferences.objects.filter(id=preference_id).first()
            if not preference:
                return JsonResponse({'error': 'Preference not found'}, status=404)

            preference.users.add(user)

            return JsonResponse({'message': 'Preference assigned to user successfully'}, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
        
class UnnassignPreferenceFromUser(APIView):
    def post(self, request, preference_id):
        session, error = authenticated_user(request)
        if error:
            return error
        try:
            user = session.user

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
        # Lists hairdressers only: customers' names and tastes are not public.
        session, error = authenticated_user(request)
        if error:
            return error
        try:
            preference = Preferences.objects.filter(id=preference_id).first()
            if not preference:
                return JsonResponse({'error': 'Preference not found'}, status=404)
            users = preference.users.filter(role='hairdresser')
            serializer = UserNameSerializer(users, many=True)
            return Response({'data':serializer.data},  status=200)
        except Exception as e:
            return Response({'error': str(e)}, status=400)
