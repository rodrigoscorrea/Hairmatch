from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import User, Customer, Hairdresser
import json
import bcrypt
from django.http import JsonResponse
import jwt, datetime
from .serializers import UserSerializer, CustomerSerializer, HairdresserSerializer

# In this file, there are 3 types of views:
# 1 - authentication views
# 2 - user accessible views - cookie managed
# 3 - user not acessible views - for admin or internal use only

# 1 - The following views are related to user authentication procedures
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
            complement=data.get('complement'),
            neighborhood=data['neighborhood'],
            city=data['city'],
            state=data['state'],
            address=data['address'],
            number=data.get('number'),
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

        return JsonResponse({'message': f"{data['role']} user registered successfully"}, status=201)


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
            return JsonResponse({'error': 'Invalid credentials'}, status=403)
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

class LogoutView(APIView):
    def post(self, request):
        response = Response()
        response.delete_cookie('jwt')
        response.data = {"message": "User logged out"}
    
        return response

class ChangePasswordView(APIView):
    
    def put(self, request):
        token = request.COOKIES.get('jwt')

        if not token: 
            return JsonResponse({'authenticated': False}, status=200)
        try:
            payload = jwt.decode(token, 'secret', algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return JsonResponse({'authenticated': False}, status=200)
        
        user = User.objects.filter(id=payload['id']).first()
        if user:
            data = json.loads(request.body)
            raw_password = data['password'].replace(' ', '')
            hashed_password = bcrypt.hashpw(raw_password.encode('utf-8'), bcrypt.gensalt())
            user.password = hashed_password.decode('utf-8')
            user.save()
            return JsonResponse({'message': 'Password updated successfully'}, status=200)

        return JsonResponse({'error': 'User not found'}, status=404)
        
# 2 - The following views are related to the User Info
# Those views only works if cookies are present in the request       
# Therefore, they can be used only if the user is logged in and are user accessible

class UserInfoCookieView(APIView):
    def get(self, request):
        token = request.COOKIES.get('jwt')

        if not token:
            return JsonResponse({'error': 'Invalid token'}, status=403)

        try:
            payload = jwt.decode(token, 'secret', algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token expired'}, status=403)
        
        try:
            user = User.objects.filter(id=payload['id']).filter(is_active=True).first()
        except User.DoesNotExist:
            return JsonResponse({'error': 'user not found'}, status=400)

        user_data = UserSerializer(user).data

        if user.role == 'customer':
            customer = Customer.objects.filter(user=user).first()
            customer_data = CustomerSerializer(customer).data
            return JsonResponse({'customer': customer_data}, status=200)
        elif user.role == 'hairdresser':
            hairdresser = Hairdresser.objects.filter(user=user).first()
            hairdresser_data = HairdresserSerializer(hairdresser).data
            return JsonResponse({'hairdresser': hairdresser_data}, status=200)    
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
            user = User.objects.filter(id=payload['id']).filter(is_active=True).first()  
            user.delete()
            response = JsonResponse({'message': 'user deleted'}, status=200)
            response.delete_cookie('jwt')
            return response
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=400)

    #This function does not handle password update procedure
    def put(self, request):
        data = json.loads(request.body)
        token = request.COOKIES.get('jwt')

        if not token:
            return JsonResponse({'error': 'Invalid token'}, status=403)

        try:
            payload = jwt.decode(token, 'secret', algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return JsonResponse({'error': 'Token expired'}, status=403)

        user = User.objects.filter(id=payload['id'], is_active=True).first()

        if not user:
            return JsonResponse({'error': 'User not found'}, status=404)

        
        existing_email = User.objects.filter(email=data['email']).first()
         
        # if there is another user with the email you want to switch, you cannot proceed 
        if existing_email and (existing_email != user): 
            return JsonResponse({'error': 'This email is already taken'}, status=403)

        allowed_fields = [
            'first_name', 'last_name', 'phone', 'email',
            'address', 'number', 'postal_code', 'rating',
            'complement', 'neighborhood', 'city', 'state'
        ]

        for field in allowed_fields:
            if field in data:
                setattr(user, field, data[field])

        user.save()

        if user.role == 'customer':
            customer = Customer.objects.filter(user=user).first()
            if customer and 'cpf' in data:
                customer.cpf = data['cpf']
                customer.save()
        elif user.role == 'hairdresser':
            hairdresser = Hairdresser.objects.filter(user=user).first()
            if hairdresser:
                if 'experience_years' in data:
                    hairdresser.experience_years = data['experience_years']
                if 'resume' in data:
                    hairdresser.resume = data['resume']
                if 'cnpj' in data:
                    hairdresser.cnpj = data['cnpj']
                hairdresser.save()

        return JsonResponse({'message': 'User updated successfully'}, status=200)

# 3 - The following views are related to the User Info
# Those views works WITHOUT the presence of cookies in the request
# Those views should only be used by admin personal or internal functions

class UserInfoView(APIView):
    
    def delete(self, request, email=None):
        token = request.COOKIES.get('jwt')
            
        user = User.objects.filter(email=email).filter(is_active=True).first()  
        if user:
            user.delete()
            response = JsonResponse({'message': 'user deleted'}, status=200)

            if token:
                response.delete_cookie('jwt')
            return response
        else:
            return JsonResponse({'error': 'User not found'}, status=400)
class LogoutView(APIView):
    def post(self, request):
        response = Response()
        response.delete_cookie('jwt')
        response.data = {"message": "User logged out"}
    
        return response