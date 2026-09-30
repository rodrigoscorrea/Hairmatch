import math

from django.db import transaction
from django.http import HttpResponse, JsonResponse
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView

from hairmatch.images import InvalidImage
from hairmatch.problems import (
    body_error,
    json_object,
    missing_field_errors,
    problem_response,
    request_data,
    validation_problem,
)
from reserve.models import Reserve
from users.authentication import authenticated_customer, forbidden
from users.models import Hairdresser

from .models import Review
from .serializers import ReviewSerializer

RATING_DETAIL = 'This field must be a number.'


def _is_id(value):
    return not isinstance(value, bool) and str(value).lstrip('-').isdigit()


def _parse_rating(value):
    """The rating as a float, or None when it is not a finite number."""
    try:
        rating = float(value)
    except (TypeError, ValueError):
        return None
    return rating if math.isfinite(rating) else None


# 2 - Cookie-based views (authenticated user)
class CreateReview(APIView):
    # Add parsers to handle multipart/form-data
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        # 1. Authenticate the user via the session cookie
        session, customer, error = authenticated_customer(request)
        if error:
            return error

        # 2. Extract data from the FormData
        data = request_data(request)
        comment = data.get('comment', '')
        picture = request.FILES.get('picture')

        # 3. Validate the fields, all at once
        errors = missing_field_errors(data, ['reserve', 'rating', 'hairdresser'])
        for field in ('reserve', 'hairdresser'):
            if data.get(field) and not _is_id(data[field]):
                errors.append(body_error(field, 'This field must be an integer.'))
        if data.get('rating') and _parse_rating(data['rating']) is None:
            errors.append(body_error('rating', RATING_DETAIL))
        if errors:
            raise validation_problem(errors)
        rating = _parse_rating(data['rating'])
        hairdresser_id = data['hairdresser']

        try:
            reserve = Reserve.objects.get(id=data['reserve'])
        except Reserve.DoesNotExist:
            return problem_response(request, 'not-found', 'Reservation not found.')

        if reserve.customer != customer:
            return forbidden(request)

        if reserve.review:
            return problem_response(request, 'review-exists', 'This reservation has already been reviewed.')

        if not Hairdresser.objects.filter(id=hairdresser_id).exists():
            return problem_response(request, 'not-found', 'Hairdresser not found.')
        # A review can only be about the hairdresser who did the reserved service
        if str(reserve.service.hairdresser_id) != str(hairdresser_id):
            raise validation_problem([body_error('hairdresser', 'The hairdresser does not match the reservation.')])

        # 4. Create the Review object in the database
        try:
            with transaction.atomic():
                new_review = Review.objects.create(
                    rating=rating,
                    comment=comment,
                    picture=picture,
                    customer=customer,
                    hairdresser_id=hairdresser_id
                )
                reserve.review = new_review
                reserve.save()
        except InvalidImage:
            return problem_response(request, 'invalid-image', 'The review picture is not a valid image.')

        return JsonResponse({'message': "Review registered successfully"}, status=201)


class ListReview(APIView):
    def get(self, request, hairdresser_id):
        reviews = Review.objects.all().filter(hairdresser_id=hairdresser_id)
        serializer = ReviewSerializer(reviews, many=True)
        return JsonResponse({'data': serializer.data}, status=200)


class UpdateReview(APIView):
    def put(self, request, id):
        session, customer, error = authenticated_customer(request)
        if error:
            return error

        review = Review.objects.filter(id=id, customer_id=customer.id).first()
        if not review:
            return problem_response(request, 'not-found', 'Review not found.')

        data = json_object(request)
        if 'rating' not in data:
            raise validation_problem([body_error('rating', 'This field is required.')])
        rating = _parse_rating(data['rating'])
        if rating is None:
            raise validation_problem([body_error('rating', RATING_DETAIL)])

        review.rating = rating
        review.comment = data.get('comment', review.comment)
        review.picture = data.get('picture', review.picture)
        review.save()
        return JsonResponse({'message': "Review updated successfully"}, status=200)
    
class RemoveReview(APIView):
    def delete(self, request, id): # Id da review
        session, customer, error = authenticated_customer(request)
        if error:
            return error

        review = Review.objects.filter(id=id, customer_id=customer.id).first()
        if not review:
            return problem_response(request, 'not-found', 'Review not found.')

        with transaction.atomic():
            reserve = Reserve.objects.filter(review=review).first()
            if reserve:
                reserve.review = None
                reserve.save()

            review.delete()
        return HttpResponse(status=204)


class ReviewDetail(UpdateReview, RemoveReview):
    """`/api/reviews/{id}`: PUT updates and DELETE removes the review of the logged customer."""
