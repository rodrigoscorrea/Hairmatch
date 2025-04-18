from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import Review
from users.models import User, Customer, Hairdresser
from .serializers import ReviewSerializer
import json
from django.http import JsonResponse
import jwt, datetime

# 2 - Cookie-based views (usuário autenticado)
class RegisterReview(APIView):
    def post(self, request):
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

            if 'rating' not in data:
                return JsonResponse({'error': 'Missing required fields: rating'}, status=400)
            review = Review.objects.create(
                rating=data['rating'],
                comment=data.get('comment', ''),
                picture=data.get('picture', ''),
                customer_id=customer.id,
                hairdresser_id=data['hairdresser']
            ) 
            serializer = ReviewSerializer(review)
            return JsonResponse({'message': "Review registered successfully"}, status=201)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)


class ListReview(APIView):
    def get(self, request, id):
        try:
            reviews = Review.objects.all().filter(hairdresser_id=id)
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
    def delete(self, request, id):
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
            review.delete()
            return JsonResponse({'message': "Review deleted successfully"}, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

