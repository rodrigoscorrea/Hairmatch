from django.urls import path
from preferences.views import CreatePreferences, ListPreferences, RemovePreferences, UpdatePreferences


urlpatterns = [
    path('create', CreatePreferences.as_view(), name='create_preferences'),
    path('list/<int:user_id>', ListPreferences.as_view(), name='list_preferences'),
    path('remove/<int:id>', RemovePreferences.as_view(), name='remove_preferences'),
    path('update/<int:id>', UpdatePreferences.as_view(), name='update_preferences'),
]
