from django.urls import path
from .views import CreateReview, CustomerRatingCollection, ListReview, ReviewDetail

urlpatterns = [
    path('reviews', CreateReview.as_view(), name='create_review'),
    path('hairdressers/<int:hairdresser_id>/reviews', ListReview.as_view(), name='list_review'),
    path('reviews/<int:id>', ReviewDetail.as_view(), name='review_detail'),
    path('customer-ratings', CustomerRatingCollection.as_view(), name='customer_ratings'),
]
