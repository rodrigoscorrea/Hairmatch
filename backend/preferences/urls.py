from django.urls import path
from .views import RegisterPreference, ListPreferences, UpdatePreference, RemovePreference ,ListPreferencesNoCookie

urlpatterns = [
    path('register', RegisterPreference.as_view(), name='register_preference'),
    path('list', ListPreferences.as_view(), name='list_preferences'),
    path('list/<int:id>', ListPreferencesNoCookie.as_view(), name='list_preferences_by_id'),
    path('update/<int:id>', UpdatePreference.as_view(), name='update_preference'),
    path('remove/<int:id>', RemovePreference.as_view(), name='remove_preference'),
]
