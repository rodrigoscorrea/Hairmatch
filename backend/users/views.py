from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import User, Customer, Hairdresser
from preferences.models import Preferences
import json
import bcrypt
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
import jwt, datetime
from .serializers import UserSerializer, CustomerSerializer, HairdresserSerializer, HairdresserFullInfoSerializer
from hairmatch.ai_clients.gemini_client import hairdresser_profile_ai_completion
from .filters import HairdresserFilter
from .serializers import SearchResultSerializer # Import our new serializer
from .filters import HairdresserFilter
from service.models import Service
from itertools import chain

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
        if User.objects.filter(phone=data['phone']).exists():
            return JsonResponse({'error': 'Phone number already exists'}, status=400)
        
        if data.get('role') is None or data['role'] is None or data['role'] == '':
            return JsonResponse({'error': 'No role assigned to user'}, status=400)
        if data.get('email') is None or data['email'] is None or data['email'] == '':
            return JsonResponse({'error': 'No email assigned to user'}, status=400)
        if data.get('password') is None or data['password'] is None or data['password'] == '':
            return JsonResponse({'error': 'No password assigned to user'}, status=400)
        if data.get('phone') is None or data['phone'] is None or data['phone'] == '':
            return JsonResponse({'error': 'No phone assigned to user'}, status=400)
        if  len(data['phone']) < 11:
            return JsonResponse({'error': 'Phone number is too short'}, status=400)

        raw_password = data['password'].replace(' ', '')
        hashed_password = bcrypt.hashpw(raw_password.encode('utf-8'), bcrypt.gensalt())
        preferences = data['preferences']
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

        if len(preferences) > 0:
            for preference in preferences:
                user.preferences.add(preference)

        # Create profile based on user type
        if data['role'] == 'customer':
            Customer.objects.create(
                user=user,
                cpf=data['cpf'],
            )
        elif data['role'] == 'hairdresser':
            Hairdresser.objects.create(
                user=user,
                cnpj=data['cnpj'],
                experience_time=data['experience_time'],
                experiences=data['experiences'],
                products=data['products'],
                resume=data['resume']
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
                response.set_cookie(
                    key='jwt', 
                    value=token, 
                    httponly=True,
                    samesite='None',
                    secure=True
                )
                response.data = {
                    'jwt': token
                }

                return response
            return JsonResponse({'error': 'Credenciais inválidas, verifique seus dados e tente novamente'}, status=403)
        return JsonResponse({'error': 'Usuário não cadastrado na base de dados'}, status=400)
    
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

class GlobalSearchView(APIView):
    def get(self, request):
        query = request.query_params.get('search', None)

        if not query:
            return Response([], status=200)

        hairdresser_queryset = Hairdresser.objects.all()
        hairdresser_filter = HairdresserFilter({'search': query}, queryset=hairdresser_queryset)
        hairdresser_results = hairdresser_filter.qs

        service_results = Service.objects.filter(
            Q(name__icontains=query)
        ) 
        combined_results = list(chain(hairdresser_results, service_results))
        serializer = SearchResultSerializer(combined_results, many=True, context={'request': request})

        return JsonResponse({'data':serializer.data}, status=200)

class UserInfoView(APIView):
    def get(self,request,email=None):
        try:
            user = User.objects.filter(email=email).filter(is_active=True).first()
        except User.DoesNotExist:
            return JsonResponse({'error': 'User not found'}, status=404)

        if user:
            if (user.role == 'customer'):
                customer = Customer.objects.get(user=user)
                customer_serialized = CustomerSerializer(customer).data
                return JsonResponse({'data': customer_serialized}, status=200)
            else: 
                hairdresser = Hairdresser.objects.get(user=user)
                hairdresser_serialized = HairdresserSerializer(hairdresser).data
                return JsonResponse({'data': hairdresser_serialized}, status=200)
            
        return JsonResponse({'error': 'User not found'}, status=404)

    
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
    
class CustomerHomeView(APIView):
    """
    API view for customer home page that returns:
    1. Hairdressers matching customer preferences in 'for_you' object
    2. 10 hairdressers for each of the specified preference categories
    """
    
    def get(self, request, email=None):
        for_you_data = []
        if email:
            try:
                customer_user = User.objects.get(email=email, role='customer')
            except User.DoesNotExist:
                return JsonResponse({'error': 'User not found'}, status=404)
            customer_preferences = customer_user.preferences.all()
            
            # Get hairdressers matching customer preferences
            hairdressers_users = User.objects.filter(
                role='hairdresser',
                preferences__in=customer_preferences
            ).distinct()

            hairdressers_for_you = Hairdresser.objects.filter(user__in=hairdressers_users)
            
            # Prepare data for for_you response
            for_you_data = HairdresserSerializer(hairdressers_for_you, many=True).data
        
        # Get hairdressers for specific preferences
        specific_preferences = ["Coloração", "Cachos", "Barbearia", "Tranças"]
        formated_preferences_name=["coloracao", "cachos", "barbearia", "trancas"]
        preference_hairdressers = {}
        
        for i in range(len(specific_preferences)):
            try:
                preference = Preferences.objects.get(name=specific_preferences[i])
                hairdressers_users = User.objects.filter(
                    role='hairdresser',
                    preferences=preference
                ).distinct()[:10]
                
                hairdressers_per_preference = Hairdresser.objects.filter(user__in=hairdressers_users)
                hairdressers_data = HairdresserSerializer(hairdressers_per_preference, many=True).data
                
                preference_hairdressers[formated_preferences_name[i]] = hairdressers_data
            except Preferences.DoesNotExist:
                preference_hairdressers[formated_preferences_name[i]] = []
        
        # Prepare the final response
        response_data = {
            'for_you': for_you_data,
            'hairdressers_by_preferences': preference_hairdressers
        }     
        return JsonResponse(response_data, status=200)
    
class GeminiChatView(APIView):
    def post(self, request):
        data = json.loads(request.body)
        result = hairdresser_profile_ai_completion(data)
        return result