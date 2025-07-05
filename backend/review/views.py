from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Review
from reserve.models import Reserve
from users.models import User, Customer, Hairdresser
from .serializers import ReviewSerializer
import json
from django.http import JsonResponse
from rest_framework.parsers import MultiPartParser, FormParser
import jwt, datetime
from django.db import transaction

# 2 - Cookie-based views (usuário autenticado)
class CreateReview(APIView):
    # Add parsers to handle multipart/form-data
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        # 1. Authenticate the user via JWT cookie
        token = request.COOKIES.get('jwt')
        if not token:
            return JsonResponse({'error': 'Unauthenticated'}, status=403)
        try:
            payload = jwt.decode(token, 'secret', algorithms=['HS256'])
            user = User.objects.filter(id=payload['id']).first()
            customer = Customer.objects.filter(user=user).first()
            if not customer:
                return JsonResponse({'error': 'User is not a valid customer'}, status=403)
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return JsonResponse({'error': 'Invalid token'}, status=403)

        # 2. Extract data from the FormData
        reserve_id=request.data.get('reserve')
        rating_str = request.data.get('rating')
        comment = request.data.get('comment', '')
        hairdresser_id = request.data.get('hairdresser')
        picture = request.FILES.get('picture')

        # 3. Perform manual validation
        if not reserve_id:
            return JsonResponse({'error': 'Missing field: reserve'}, status=400)
        
        try:
            reserve = Reserve.objects.get(id=reserve_id)
        except Reserve.DoesNotExist:
            return JsonResponse({'error': 'Reserve not found'}, status=404)

        if reserve.customer != customer:
            return JsonResponse({'error': 'You are not authorized to review this reservation'}, status=403)

        if reserve.review:
            return JsonResponse({'error': 'This reservation has already been reviewed'}, status=409)
        if not rating_str:
            return JsonResponse({'error': 'Missing field: rating'}, status=400)
        try:
            rating = float(rating_str)
        except ValueError:
            return JsonResponse({'error': 'Invalid value for rating'}, status=400)

        if not hairdresser_id:
            return JsonResponse({'error': 'Missing field: hairdresser'}, status=400)
        
        if not Hairdresser.objects.filter(id=hairdresser_id).exists():
            return JsonResponse({'error': 'Hairdresser not found'}, status=404)

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
            
            return JsonResponse({'message': "Review registered successfully"}, status=201)
        except Exception as error:
            return JsonResponse({'error': str(error)}, status=500)


class ListReview(APIView):
    def get(self, request, hairdresser_id):
        try:
            reviews = Review.objects.all().filter(hairdresser_id=hairdresser_id)
            serializer = ReviewSerializer(reviews, many=True)
            return JsonResponse({'data': serializer.data}, status=200)
           
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


class UpdateReview(APIView):
    def put(self, request, id):
        token = request.COOKIES.get('jwt')

        if not token:
            return JsonResponse({'error': 'Invalid token'}, status=403)

        try:
            payload = jwt.decode(token, 'secret', algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token expired'}, status=403)

        try:
            data = json.loads(request.body)
            user = User.objects.filter(id=payload['id']).first()
            if not user:
                return JsonResponse({'error': 'User not found'}, status=404)
            customer = Customer.objects.filter(user=user).first()
            if user.role != 'customer':
                return JsonResponse({'error': 'User is not a customer'}, status=403)

            review = Review.objects.filter(id=id, customer_id=customer.id).first()
            if not review:
                return JsonResponse({'error': 'Review not found'}, status=404)
            if 'rating' not in data:
                return JsonResponse({'error': 'Missing required fields: rating'}, status=400)
            review.rating = data['rating']
            review.comment = data.get('comment', review.comment)
            review.picture = data.get('picture', review.picture)
            review.save()
            serializer = ReviewSerializer(review)
            return JsonResponse({'message': "Review updated successfully"}, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    
class RemoveReview(APIView):
    def delete(self, request, id): # Id da review
        token = request.COOKIES.get('jwt')

        if not token:
            return JsonResponse({'error': 'Invalid token'}, status=403)

        try:
            payload = jwt.decode(token, 'secret', algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token expired'}, status=403)

        try:
            user = User.objects.filter(id=payload['id']).first()
            if not user:
                return JsonResponse({'error': 'User not found'}, status=404)
            customer = Customer.objects.filter(user=user).first()
            if user.role != 'customer':
                return JsonResponse({'error': 'User is not a customer'}, status=403)

            review = Review.objects.filter(id=id, customer_id=customer.id).first()
            if not review:
                return JsonResponse({'error': 'Review not found'}, status=404)
            review.delete()
            return JsonResponse({'message': "Review deleted successfully"}, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

class RemoveReviewAdmin(APIView):
    def delete(self, request, id): # Id da review
        try:
            review = Review.objects.filter(id=id).first()
            if not review:
                return JsonResponse({'error': 'Review not found'}, status=404)
            review.delete()
            return JsonResponse({'message': "Review deleted successfully"}, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
