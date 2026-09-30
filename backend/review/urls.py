from django.urls import path
from .views import CreateReview, ListReview, UpdateReview, RemoveReview

urlpatterns = [
    path('register', CreateReview.as_view(), name='create_review'),
    path('list/<int:hairdresser_id>', ListReview.as_view(), name='list_review'),
    path('update/<int:id>', UpdateReview.as_view(), name='update_review'),
    path('remove/<int:id>', RemoveReview.as_view(), name='remove_review'),
    ]