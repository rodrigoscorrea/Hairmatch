"""
URL configuration for hairmatch project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, re_path, include
from hairmatch.problems import api_not_found

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('users.urls')),
    path('api/', include('preferences.urls')),
    path('api/', include('review.urls')),
    path('api/', include('availability.urls')),
    path('api/reserve/', include('reserve.urls')),
    path('api/agenda/', include('agenda.urls')),
    path('api/service/', include('service.urls')),
    path('api/chatbot/', include('chatbot.urls')),
    # Must stay last: a URL under /api/ that no route matched.
    re_path(r'^api(?:/|$)', api_not_found),
]
