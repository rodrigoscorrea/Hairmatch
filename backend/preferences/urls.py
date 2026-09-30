from django.urls import path
from preferences.views import ListPreferences, ListAllPreferences, UserPreferenceView, ListUsersPerPreference

urlpatterns = [
    path('preferences', ListAllPreferences.as_view(), name='list_all_preferences'),
    path('preferences/<int:preference_id>/users', ListUsersPerPreference.as_view(), name='list_users_per_preference'),
    path('users/<int:user_id>/preferences', ListPreferences.as_view(), name='list_preferences'),
    path('users/me/preferences/<int:preference_id>', UserPreferenceView.as_view(), name='user_preference'),
]
