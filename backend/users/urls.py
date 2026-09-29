from django.urls import path
from .views import (
    RegisterView, 
    LoginView, 
    RefreshView,
    GoogleAuthView,
    CepLookupView,
    LogoutView, 
    GlobalSearchView,
    UserInfoCookieView, 
    UserInfoView, 
    ChangePasswordView, 
    CustomerHomeView, 
    HairdresserInfoView,
    GeminiChatView
)

urlpatterns = [
    path('auth/register', RegisterView.as_view(), name='register'),
    path('auth/login', LoginView.as_view(), name='login'),
    path('auth/user', LoginView.as_view(), name='user_auth'),
    path('auth/refresh', RefreshView.as_view(), name='refresh'),
    path('auth/google', GoogleAuthView.as_view(), name='google_auth'),
    path('auth/change-password', ChangePasswordView.as_view(), name='password_change'),
    path('auth/logout', LogoutView.as_view(), name='logout'),
    path('address/cep/<str:cep>', CepLookupView.as_view(), name='cep_lookup'),
    path('user/search', GlobalSearchView.as_view(), name='global_search'), 
    path('user/authenticated', UserInfoCookieView.as_view(), name='user_info_auth'),
    path('user/<str:email>', UserInfoView.as_view(), name='user_info'),
    path('customer/home', CustomerHomeView.as_view(), name='customer_home_info'),
    path('customer/home/<str:email>', CustomerHomeView.as_view(), name='customer_home_info'),
    path('hairdresser/<int:hairdresser_id>', HairdresserInfoView.as_view(), name='hairdresser_info'),
    path('hairdresser/gemini_completion', GeminiChatView.as_view(), name='gemini_completion'),
]