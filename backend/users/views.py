from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import User, Customer, Hairdresser
import json
import bcrypt
from django.http import JsonResponse
import jwt, datetime
from .serializers import UserSerializer, CustomerSerializer, HairdresserSerializer

# Create your views here.
class RegisterView(APIView):
    def post(self, request):    
        data = json.loads(request.body)

        if User.objects.filter(email=data['email']).exists():
            return JsonResponse({'error': 'User already exists'}, status=400)
        
        if data.get('role') is None:
            return JsonResponse({'error': 'No role assigned to user'}, status=400)

        raw_password = data['password'].replace(' ', '')
        hashed_password = bcrypt.hashpw(raw_password.encode('utf-8'), bcrypt.gensalt())

        user = User.objects.create(
            first_name=data['first_name'],
            last_name=data['last_name'],
            phone=data['phone'],
            number=data['number'],
            street=data['street'],
            postal_code=data['postal_code'],
            email=data['email'],
            password=hashed_password.decode('utf-8'),
            role=data['role'],
            rating=data['rating']
        )

        # Create profile based on user type
        if data['role'] == 'customer':
            Customer.objects.create(
                user=user,
                cpf=data['cpf'],
            )
        elif data['role'] == 'hairdresser':
            Hairdresser.objects.create(
                user=user,
                resume=data['resume'],
                cnpj=data['cnpj'],
                experience_years=data['experience_years']
            )

        return JsonResponse({'message': 'User registered successfully'}, status=201)

class LoginView(APIView):
    def post(self,request):
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')
        
        user = User.objects.filter(email=email).first()
        if user:
            stored_password = user.password.encode('utf-8')

            if bcrypt.checkpw(password.encode('utf-8'), stored_password):

                payload = {
                    'id': user.id,
                    'exp': datetime.datetime.now() + datetime.timedelta(minutes=60),
                    'iat': datetime.datetime.now()
                }

                token = jwt.encode(payload, 'secret', algorithm='HS256')

                response = JsonResponse({'message': 'Login successful'}, status=200)
                response.set_cookie(key='jwt', value=token, httponly=True)
                response.data = {
                    'jwt': token
                }

                return response
            return JsonResponse({'error': 'Invalid credentials'}, status=501)
        return JsonResponse({'error': 'User does not exist'}, status=400)
    
    def get(self, request):
        token = request.COOKIES.get('jwt')

        if not token: 
            return JsonResponse({'authenticated': False}, status=200)

        try:
            payload = jwt.decode(token, 'secret', algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return JsonResponse({'authenticated': False}, status=200)
        
        user = User.objects.filter(id=payload['id']).first()
        
        return JsonResponse({"authenticated":True}, status=200)

class UserInfoView(APIView):
    def get(self, request):
        token = request.COOKIES.get('jwt')

        if not token:
            return JsonResponse({'error': 'Invalid token'}, status=403)

        try:
            payload = jwt.decode(token, 'secret', algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token expired'}, status=403)
        
        user = User.objects.filter(id=payload['id']).first()
        user_data = UserSerializer(user).data

        if user.role == 'customer':
            customer = Customer.objects.filter(user=user).first()
            customer_data = CustomerSerializer(customer).data
            return JsonResponse({'user': customer_data}, status=200)
        elif user.role == 'hairdresser':
            hairdresser = Hairdresser.objects.filter(user=user).first()
            hairdresser_data = HairdresserSerializer(hairdresser).data
            return JsonResponse({'user': hairdresser_data}, status=200)    
        else: 
            return JsonResponse({'error': 'error retrieving user with role'}, status=500)

    def delete(self, request):
        token = request.COOKIES.get('jwt')

        if not token:
            return JsonResponse({'error': 'Invalid token'}, status=403)

        try:
            payload = jwt.decode(token, 'secret', algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token expired'}, status=403)
        
        try:
            user = User.objects.filter(id=payload['id']).first()  
            user.delete()
            response = JsonResponse({'message': 'user deleted'}, status=200)
            response.delete_cookie('jwt')
            return response
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=400)

    def put(self, request):
        data = json.loads(request.body)
        token = request.COOKIES.get('jwt')

        if not token:
            return JsonResponse({'error': 'Invalid token'}, status=403)

        try:
            payload = jwt.decode(token, 'secret', algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token expired'}, status=403)

        try:
            user = User.objects.filter(id=payload['id']).first()  
            
            if user.is_valid():
                return JsonResponse({'messahe': 'user valido'}, status=200)
            #response = JsonResponse({'message': 'user deleted'}, status=200)
            #response.delete_cookie('jwt')
            return JsonResponse({'message': 'user invalido'}, status=300)
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=400)
class LogoutView(APIView):
    def post(self, request):
        response = Response()
        response.delete_cookie('jwt')
        response.data = {"message": "User logged out"}
    
        return response