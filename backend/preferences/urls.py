from django.urls import path
from preferences.views import ListPreferences, ListAllPreferences, AssignPreferenceToUser, UnnassignPreferenceFromUser, ListUsersPerPreference


urlpatterns = [
    path('list/<int:users>', ListPreferences.as_view(), name='list_preferences'),
    path('list', ListAllPreferences.as_view(), name='list_all_preferences'),
    path('list/users/<int:preference_id>', ListUsersPerPreference.as_view(), name='list_users_per_preference'),
    path('assign/cookie/<int:preference_id>', AssignPreferenceToUser.as_view(), name='assign_preferences_to_user'),
    path('unassign/<int:preference_id>', UnnassignPreferenceFromUser.as_view(), name='unassign_preferences_from_user'),
]
