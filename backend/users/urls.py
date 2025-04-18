from django.urls import path
from .views import RegisterView, LoginView, LogoutView, UserInfoView

urlpatterns = [
    path('auth/register', RegisterView.as_view(), name='register'),
    path('auth/login', LoginView.as_view(), name='login'),
    path('auth/user', LoginView.as_view(), name='user_auth'),
    path('user', UserInfoView.as_view(), name='user_info'),
    path('auth/logout', LogoutView.as_view(), name='logout')
]