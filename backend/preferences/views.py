from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Preferences
from users.models import User
from users.serializers import UserNameSerializer
from .serializers import PreferencesSerializer
from django.http import HttpResponse
import json
from hairmatch.problems import problem_response
from users.authentication import authenticated_user

# Create your views here.
# The catalog comes from the populate_preferences seed; the API does not create, edit or remove it.
class UserPreferenceView(APIView):
    """PUT assigns and DELETE unassigns a preference of the logged user. Both are idempotent and answer 204."""

    def put(self, request, preference_id):
        session, error = authenticated_user(request)
        if error:
            return error

        preference = Preferences.objects.filter(id=preference_id).first()
        if not preference:
            return problem_response(request, 'not-found', 'Preference not found.')

        preference.users.add(session.user)

        return HttpResponse(status=204)

    def delete(self, request, preference_id):
        session, error = authenticated_user(request)
        if error:
            return error

        preference = Preferences.objects.filter(id=preference_id).first()
        if not preference:
            return problem_response(request, 'not-found', 'Preference not found.')

        preference.users.remove(session.user)

        return HttpResponse(status=204)


class ListPreferences(APIView):
    def get(self, request, user_id):
        preferences = Preferences.objects.filter(users=user_id)
        if not preferences.exists():
            return problem_response(request, 'not-found', 'Preferences not found.')
        serializer = PreferencesSerializer(preferences, many=True)
        return Response(serializer.data)
        
class ListAllPreferences(APIView):
    def get(self, request):
        preferences = Preferences.objects.all()
        serializer = PreferencesSerializer(preferences, many=True)
        return Response(serializer.data)

class ListUsersPerPreference(APIView):
    def get(self, request, preference_id):
        # Lists hairdressers only: customers' names and tastes are not public.
        session, error = authenticated_user(request)
        if error:
            return error

        preference = Preferences.objects.filter(id=preference_id).first()
        if not preference:
            return problem_response(request, 'not-found', 'Preference not found.')
        users = preference.users.filter(role='hairdresser', is_active=True)
        serializer = UserNameSerializer(users, many=True)
        return Response({'data':serializer.data},  status=200)
