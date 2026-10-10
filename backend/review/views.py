import math

from django.db import transaction
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
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
from hairmatch.storage import delete_stored_files
from reserve.models import Reserve
from users.authentication import authenticated_customer, authenticated_hairdresser, authenticated_user, forbidden
from users.models import Customer, Hairdresser

from .customer_ratings import ALREADY_RATED_DETAIL, record_customer_rating, service_end
from .models import CustomerRating, Review, ReviewPicture
from .pictures import INVALID_REVIEW_PICTURE_DETAIL, add_review_pictures, picture_errors, picture_names
from .serializers import (
    CustomerRatingCreatedSerializer,
    CustomerRatingSerializer,
    ReviewPictureSerializer,
    ReviewSerializer,
)

RATING_DETAIL = 'This field must be a number.'
RATING_RANGE_DETAIL = 'The rating must be between 1 and 5.'
MIN_RATING, MAX_RATING = 1, 5
MAX_COMMENT_LENGTH = 500
REQUIRED_DETAIL = 'This field is required.'


def _is_id(value):
    return not isinstance(value, bool) and str(value).lstrip('-').isdigit()


def _parse_rating(value):
    """The rating as a float, or None when it is not a finite number."""
    try:
        rating = float(value)
    except (TypeError, ValueError):
        return None
    return rating if math.isfinite(rating) else None


def _rating_error(value):
    """The `errors` item for a rating that is not a number from 1 to 5, or None for a valid one."""
    rating = _parse_rating(value)
    if rating is None:
        return body_error('rating', RATING_DETAIL)
    if not MIN_RATING <= rating <= MAX_RATING:
        return body_error('rating', RATING_RANGE_DETAIL)
    return None


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
        files = request.FILES.getlist('pictures')

        # 3. Validate the fields, all at once
        errors = missing_field_errors(data, ['reserve', 'rating', 'hairdresser'])
        for field in ('reserve', 'hairdresser'):
            if data.get(field) and not _is_id(data[field]):
                errors.append(body_error(field, 'This field must be an integer.'))
        rating_error = _rating_error(data['rating']) if data.get('rating') else None
        if rating_error:
            errors.append(rating_error)
        errors += picture_errors(files)
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

        # 4. Create the Review and its pictures. The pictures reach the storage while the rows are written, so a
        # request that fails afterwards deletes them at once: the rollback would never run an on_commit hook.
        saved_names = []
        try:
            with transaction.atomic():
                new_review = Review.objects.create(
                    rating=rating,
                    comment=comment,
                    customer=customer,
                    hairdresser_id=hairdresser_id
                )
                add_review_pictures(new_review, files, saved_names)
                reserve.review = new_review
                reserve.save()
        except InvalidImage:
            delete_stored_files(saved_names)
            return problem_response(request, 'invalid-image', INVALID_REVIEW_PICTURE_DETAIL)
        except BaseException:
            delete_stored_files(saved_names)
            raise

        return JsonResponse({'message': "Review registered successfully"}, status=201)


class ListReview(APIView):
    def get(self, request, hairdresser_id):
        reviews = (
            Review.objects.filter(hairdresser_id=hairdresser_id)
            .select_related('customer__user')
            .prefetch_related('pictures')
            .order_by('id')  # the joins above leave the order to the planner otherwise
        )
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
        rating_error = _rating_error(data['rating'])
        if rating_error:
            raise validation_problem([rating_error])

        review.rating = _parse_rating(data['rating'])
        review.comment = data.get('comment', review.comment)
        # The picture only arrives as an upload on create: a JSON string here would become an arbitrary storage key.
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

            # The CASCADE removes the rows but not the objects: they go after the commit, never on a rollback.
            names = picture_names(review.pictures.all())
            review.delete()
            transaction.on_commit(lambda: delete_stored_files(names))
        return HttpResponse(status=204)


class ReviewDetail(UpdateReview, RemoveReview):
    """`/api/reviews/{id}`: PUT updates and DELETE removes the review of the logged customer."""


class ReviewPictureCollection(APIView):
    """`/api/reviews/{id}/pictures`: POST adds pictures to a review of the logged customer, up to 5 in all."""
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, id):
        session, customer, error = authenticated_customer(request)
        if error:
            return error

        # What does not depend on the review is refused first, so invalid input never answers 404.
        files = request.FILES.getlist('pictures')
        errors = picture_errors(files, required=True)
        if errors:
            raise validation_problem(errors)

        saved_names = []
        try:
            with transaction.atomic():
                # Locked before the count, so two requests cannot both fit under the limit.
                review = Review.objects.select_for_update().filter(id=id, customer_id=customer.id).first()
                if review is None:
                    return problem_response(request, 'not-found', 'Review not found.')
                errors = picture_errors(files, existing=review.pictures.count())
                if errors:
                    raise validation_problem(errors)
                add_review_pictures(review, files, saved_names)
        except InvalidImage:
            delete_stored_files(saved_names)
            return problem_response(request, 'invalid-image', INVALID_REVIEW_PICTURE_DETAIL)
        except BaseException:
            delete_stored_files(saved_names)
            raise

        return JsonResponse({'data': ReviewPictureSerializer(review.pictures.all(), many=True).data}, status=201)


class ReviewPictureDetail(APIView):
    """`/api/reviews/{id}/pictures/{picture_id}`: DELETE removes one picture of a review of the logged customer."""

    def delete(self, request, id, picture_id):
        session, customer, error = authenticated_customer(request)
        if error:
            return error

        review = Review.objects.filter(id=id, customer_id=customer.id).first()
        if review is None:
            return problem_response(request, 'not-found', 'Review not found.')
        picture = ReviewPicture.objects.filter(id=picture_id, review=review).first()
        if picture is None:
            return problem_response(request, 'not-found', 'Picture not found.')

        with transaction.atomic():
            name = picture.picture.name
            picture.delete()
            # The object goes after the commit, never on a rollback.
            transaction.on_commit(lambda: delete_stored_files([name]))
        return HttpResponse(status=204)


def _customer_rating_errors(data):
    """The `errors` items of a POST /api/customer-ratings body, one per invalid field."""
    errors = []
    reservation = data.get('reservation')
    if reservation is None or reservation == '':
        errors.append(body_error('reservation', REQUIRED_DETAIL))
    elif not _is_id(reservation):
        errors.append(body_error('reservation', 'This field must be an integer.'))

    # A JSON integer only: the app sends whole stars, so 4.5, "5" and true are refused.
    rating = data.get('rating')
    if rating is None:
        errors.append(body_error('rating', REQUIRED_DETAIL))
    elif isinstance(rating, bool) or not isinstance(rating, int) or not MIN_RATING <= rating <= MAX_RATING:
        errors.append(body_error('rating', 'The rating must be an integer from 1 to 5.'))

    comment = data.get('comment')
    if comment is not None and not isinstance(comment, str):
        errors.append(body_error('comment', 'The comment must be a string.'))
    elif comment is not None and len(comment.strip()) > MAX_COMMENT_LENGTH:
        errors.append(body_error('comment', f'The comment must have at most {MAX_COMMENT_LENGTH} characters.'))
    return errors


def _is_rated(reservation):
    return CustomerRating.objects.filter(reservation=reservation).exists()


class CustomerRatingCollection(APIView):
    """`/api/customer-ratings`: POST rates the customer of a reservation whose service has ended."""

    def post(self, request):
        session, hairdresser, error = authenticated_hairdresser(request)
        if error:
            return error

        # The whole body is checked before the reservation is looked up: invalid input is always a 400.
        data = json_object(request)
        errors = _customer_rating_errors(data)
        if errors:
            raise validation_problem(errors)
        comment = (data.get('comment') or '').strip() or None

        try:
            reservation = Reserve.objects.select_related('service', 'customer__user').get(id=data['reservation'])
        except Reserve.DoesNotExist:
            return problem_response(request, 'not-found', 'Reservation not found.')
        if reservation.service.hairdresser_id != hairdresser.id:
            return forbidden(request)
        if _is_rated(reservation):
            return problem_response(request, 'review-exists', ALREADY_RATED_DETAIL)
        end = service_end(reservation)
        if end is None or timezone.now() < end:
            return problem_response(
                request, 'service-not-finished', 'The service of this reservation has not finished yet.'
            )

        customer_rating = record_customer_rating(hairdresser, reservation, data['rating'], comment)
        return JsonResponse({'data': CustomerRatingCreatedSerializer(customer_rating).data}, status=201)


class CustomerRatingsByCustomer(APIView):
    """
    `/api/customers/{id}/ratings`: the customer's average and count, which any hairdresser may see, and the
    ratings with their comments: all of them for the customer, only their own for a hairdresser.
    """

    def get(self, request, customer_id):
        session, error = authenticated_user(request)
        if error:
            return error

        try:
            customer = Customer.objects.select_related('user').get(id=customer_id)
        except Customer.DoesNotExist:
            return problem_response(request, 'not-found', 'Customer not found.')

        ratings = CustomerRating.objects.filter(customer=customer)
        count = ratings.count()
        if customer.user_id != session.user.id:
            hairdresser = Hairdresser.objects.filter(user=session.user).first()
            if hairdresser is None:
                return forbidden(request)
            ratings = ratings.filter(hairdresser=hairdresser)

        ratings = ratings.select_related('reservation__service', 'hairdresser__user').order_by('-created_at', '-id')
        return JsonResponse({'data': {
            'average': customer.user.rating,
            'count': count,
            'ratings': CustomerRatingSerializer(ratings, many=True).data,
        }}, status=200)
