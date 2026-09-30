from django.urls import path
from .views import (
    RegisterView,
    LoginView,
    SessionView,
    RefreshView,
    GoogleAuthView,
    CepLookupView,
    LogoutView,
    GlobalSearchView,
    CurrentUserView,
    ChangePasswordView,
    CustomerHomeView,
    HomeView,
    HairdresserInfoView,
    GeminiChatView
)

urlpatterns = [
    path('users', RegisterView.as_view(), name='register'),
    path('users/me', CurrentUserView.as_view(), name='current_user'),
    path('users/me/password', ChangePasswordView.as_view(), name='password_change'),
    path('auth/session', SessionView.as_view(), name='session'),
    path('auth/login', LoginView.as_view(), name='login'),
    path('auth/refresh', RefreshView.as_view(), name='refresh'),
    path('auth/google', GoogleAuthView.as_view(), name='google_auth'),
    path('auth/logout', LogoutView.as_view(), name='logout'),
    path('postal-codes/<str:cep>', CepLookupView.as_view(), name='cep_lookup'),
    path('search', GlobalSearchView.as_view(), name='global_search'),
    path('home', HomeView.as_view(), name='home'),
    path('customers/me/home', CustomerHomeView.as_view(), name='customer_home'),
    path('hairdressers/description-drafts', GeminiChatView.as_view(), name='gemini_completion'),
    path('hairdressers/<int:hairdresser_id>', HairdresserInfoView.as_view(), name='hairdresser_info'),
]
