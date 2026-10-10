from django.urls import path
from favorite.views import FavoriteHairdresserDetail

urlpatterns = [
    path('customers/me/favorite-hairdressers/<int:hairdresser_id>', FavoriteHairdresserDetail.as_view(), name='favorite_hairdresser'),
]
