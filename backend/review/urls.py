from django.urls import path
from .views import RegisterReview, ListReview, UpdateReview, RemoveReview

urlpatterns = [
    path('register', RegisterReview.as_view(), name='register_review'),
    path('list/<int:id>', ListReview.as_view(), name='list_review'),
    path('update/<int:id>', UpdateReview.as_view(), name='update_review'),
    path('remove/<int:id>', RemoveReview.as_view(), name='remove_review'),
    ]