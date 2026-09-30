from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import User, Customer, Hairdresser
from hairmatch.images import InvalidImage
from preferences.models import Preferences
import json
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from .serializers import UserSerializer, CustomerSerializer, HairdresserSerializer, HairdresserFullInfoSerializer, PublicHairdresserSerializer
from hairmatch.ai_clients.gemini_client import hairdresser_profile_ai_completion
from .filters import HairdresserFilter
from .serializers import SearchResultSerializer # Import our new serializer
from .filters import HairdresserFilter
from service.models import Service
from itertools import chain
from rest_framework.parsers import MultiPartParser, FormParser
from preferences.models import Preferences
from django.db import transaction
from .auth_tokens import set_session_cookie, set_cognito_cookies, set_access_cookie, clear_auth_cookies, create_signup_token, decode_signup_token, InvalidSignupToken
from .authentication import (
    CUSTOMER_REQUIRED_DETAIL,
    authenticate_request,
    authenticate_token,
    authenticated_user,
    forbidden,
    is_own_email,
)
from .cognito import (
    CognitoError,
    CognitoUnavailable,
    InvalidCredentials,
    InvalidPassword,
    TooManyRequests,
    UserAlreadyExists,
    get_cognito,
)
from .google_auth import verify_google_id_token, GoogleTokenError
from .cep_lookup import lookup_cep, InvalidCep, CepNotFound, CepServiceUnavailable
from rest_framework.throttling import AnonRateThrottle
from hairmatch.problems import Problem, body_error, json_object, problem_response, request_data, validation_problem

GOOGLE_SIGNUP_REQUIRED_FIELDS = [
    'first_name', 'last_name', 'phone', 'address',
    'neighborhood', 'city', 'state', 'postal_code',
]
ROLE_DOCUMENT_FIELD = {'customer': 'cpf', 'hairdresser': 'cnpj'}
PASSWORD_POLICY_MESSAGE = 'A senha deve ter ao menos 8 caracteres, com letra maiúscula, letra minúscula e número.'
EMAIL_TAKEN_MESSAGE = 'Usuário já está cadastrado na nossa base de dados'
PHONE_TAKEN_MESSAGE = 'O número de telefone inserido já está cadastrado na nossa base de dados'
PASSWORD_POLICY_DETAIL = 'The password must have at least 8 characters, with an uppercase letter, a lowercase letter and a number.'
PHONE_TAKEN_DETAIL = 'This phone number is already registered.'


def normalize_phone(phone):
    """The stored form of a phone typed at sign-up: its digits after the country code 55 (the chatbot looks users up by it)."""
    return f"55{''.join(ch for ch in str(phone) if ch.isdigit())}"


def _cognito_error_response(request, error):
    if isinstance(error, TooManyRequests):
        return problem_response(request, 'too-many-requests', 'Too many attempts. Wait and try again.')
    return problem_response(request, 'auth-unavailable', 'The authentication service is unavailable. Try again shortly.')


def _string_field_errors(data, fields):
    """One `errors` item per field of `fields` that is absent, empty or not a string."""
    errors = []
    for field in fields:
        value = data.get(field)
        if value is None or value == '':
            errors.append(body_error(field, 'This field is required.'))
        elif not isinstance(value, str):
            errors.append(body_error(field, 'This field must be a string.'))
    return errors


def _delete_account(request, user):
    """Deletes the Cognito user (e-mail accounts) and the row, and clears the session cookies."""
    if user.cognito_sub:
        try:
            get_cognito().admin_delete_user(user.email)
        except CognitoError as err:
            return _cognito_error_response(request, err)
    user.delete()
    return clear_auth_cookies(HttpResponse(status=204))


def _discard_cognito_user(email):
    """Undoes a sign-up whose Postgres rows could not be created."""
    try:
        get_cognito().admin_delete_user(email)
    except CognitoError:
        pass  # already logged by the service; the original error is what the caller reports


# In this file, there are 3 types of views:
# 1 - authentication views
# 2 - user accessible views - cookie managed
# 3 - user not acessible views - for admin or internal use only

# 1 - The following views are related to user authentication procedures
class RegisterView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):    
        if request.data.get('google_signup_token'):
            return self._register_with_google(request)

        email = request.data.get('email')
        password = request.data.get('password')
        phone = request.data.get('phone')
        role = request.data.get('role')
        if User.objects.filter(email=email).exists():
            return JsonResponse({'error': EMAIL_TAKEN_MESSAGE}, status=409)

        if role is None or role is None or role == '':
            return JsonResponse({'error': 'No role assigned to user'}, status=400)
        if email is None or email is None or email == '':
            return JsonResponse({'error': 'No email assigned to user'}, status=400)
        if password is None or password is None or password == '':
            return JsonResponse({'error': 'No password assigned to user'}, status=400)
        if phone is None or phone is None or phone == '':
            return JsonResponse({'error': 'No phone assigned to user'}, status=400)
        if  len(phone) < 10:
            return JsonResponse({'error': 'Phone number is too short'}, status=400)
        if User.objects.filter(phone=normalize_phone(phone)).exists():
            return JsonResponse({'error': PHONE_TAKEN_MESSAGE}, status=409)

        try:
            cognito_sub = get_cognito().sign_up_confirmed(email, password)
        except InvalidPassword:
            return JsonResponse({'error': PASSWORD_POLICY_MESSAGE}, status=400)
        except UserAlreadyExists:
            return JsonResponse({'error': EMAIL_TAKEN_MESSAGE}, status=409)
        except CognitoError as err:
            return _cognito_error_response(request, err)

        try:
            with transaction.atomic():
                user = User.objects.create(
                    first_name=request.data.get('first_name'),
                    last_name=request.data.get('last_name'),
                    phone=normalize_phone(phone),
                    complement=request.data.get('complement'),
                    neighborhood=request.data.get('neighborhood'),
                    city=request.data.get('city'),
                    state=request.data.get('state'),
                    address=request.data.get('address'),
                    number=request.data.get('number'),
                    postal_code=request.data.get('postal_code'),
                    email=request.data.get('email'),
                    password=None,
                    cognito_sub=cognito_sub,
                    role=request.data.get('role'),
                    rating=request.data.get('rating'),
                )

                if 'profile_picture' in request.FILES:
                    user.profile_picture = request.FILES['profile_picture']
                    user.save()

                _create_role_profile(user, request.data)
        except InvalidImage:
            failure = JsonResponse({'error': 'Imagem de perfil inválida.'}, status=400)
        except json.JSONDecodeError:
            failure = JsonResponse({'error': 'Invalid Preferences JSON'}, status=400)
        except Exception:
            failure = JsonResponse({'error': 'Erro ao criar a conta.'}, status=500)
        else:
            return JsonResponse({'message': f"{role} user registered successfully"}, status=201)

        _discard_cognito_user(email)
        return failure

    def _register_with_google(self, request):
        data = request.data
        try:
            claims = decode_signup_token(data.get('google_signup_token'))
        except InvalidSignupToken:
            return JsonResponse({'error': 'Sua sessão de cadastro com o Google expirou. Entre com o Google novamente.'}, status=401)

        role = data.get('role')
        if not role:
            return JsonResponse({'error': 'Campo obrigatório ausente: role'}, status=400)
        if role not in ROLE_DOCUMENT_FIELD:
            return JsonResponse({'error': 'Papel de usuário inválido.'}, status=400)
        for field in GOOGLE_SIGNUP_REQUIRED_FIELDS + [ROLE_DOCUMENT_FIELD[role]]:
            if not data.get(field):
                return JsonResponse({'error': f'Campo obrigatório ausente: {field}'}, status=400)
        phone = data.get('phone')
        if len(phone) < 10:
            return JsonResponse({'error': 'O número de telefone informado é muito curto.'}, status=400)

        # The e-mail comes from the signup token; form email/password fields are ignored.
        email = claims['email']
        google_id = claims['sub']
        if User.objects.filter(email__iexact=email).exists():
            return JsonResponse({'error': 'Usuário já está cadastrado na nossa base de dados'}, status=409)
        if User.objects.filter(google_id=google_id).exists():
            return JsonResponse({'error': 'Esta conta Google já está cadastrada na nossa base de dados'}, status=409)
        if User.objects.filter(phone=normalize_phone(phone)).exists():
            return JsonResponse({'error': PHONE_TAKEN_MESSAGE}, status=409)

        try:
            with transaction.atomic():
                user = User.objects.create(
                    first_name=data.get('first_name'),
                    last_name=data.get('last_name'),
                    phone=normalize_phone(phone),
                    complement=data.get('complement'),
                    neighborhood=data.get('neighborhood'),
                    city=data.get('city'),
                    state=data.get('state'),
                    address=data.get('address'),
                    number=data.get('number'),
                    postal_code=data.get('postal_code'),
                    email=email,
                    password=None,
                    google_id=google_id,
                    role=role,
                    rating=data.get('rating'),
                )
                if 'profile_picture' in request.FILES:
                    user.profile_picture = request.FILES['profile_picture']
                    user.save()
                _create_role_profile(user, data)
        except InvalidImage:  # before ValueError, which it subclasses
            return JsonResponse({'error': 'Imagem de perfil inválida.'}, status=400)
        except ValueError:
            return JsonResponse({'error': 'As preferências enviadas são inválidas.'}, status=400)
        except Exception:
            return JsonResponse({'error': 'Erro ao criar a conta.'}, status=500)

        return set_session_cookie(JsonResponse({'message': f"{role} user registered successfully"}, status=201), user)


def _create_role_profile(user, data):
    # Raises json.JSONDecodeError (a ValueError) when preferences is not valid JSON.
    preferences_ids = json.loads(data.get('preferences', '[]'))
    if isinstance(preferences_ids, list) and len(preferences_ids) > 0:
        user.preferences.clear()
        preferences_to_add = Preferences.objects.filter(id__in=preferences_ids)
        user.preferences.add(*preferences_to_add)

    # Create profile based on user type
    role = data.get('role')
    if role == 'customer':
        Customer.objects.create(
            user=user,
            cpf=data.get('cpf'),
        )
    elif role == 'hairdresser':
        Hairdresser.objects.create(
            user=user,
            cnpj=data.get('cnpj'),
            experience_time=data.get('experience_time'),
            experiences=data.get('experiences'),
            products=data.get('products'),
            resume=data.get('resume')
        )


class LoginView(APIView):
    def post(self, request):
        data = json_object(request)
        errors = _string_field_errors(data, ['email', 'password'])
        if errors:
            raise validation_problem(errors)
        email = data['email']
        password = data['password']

        if User.objects.filter(
            email__iexact=email, cognito_sub__isnull=True
        ).exclude(google_id__isnull=True).exists():
            return problem_response(
                request, 'google-account-login', 'This account uses Google sign-in. Use the Sign in with Google button.'
            )

        invalid_credentials = problem_response(request, 'invalid-credentials', 'Invalid email or password.')
        try:
            tokens = get_cognito().authenticate(email, password)
            session = authenticate_token(tokens.access_token)
        except InvalidCredentials:
            return invalid_credentials
        except CognitoError as err:
            return _cognito_error_response(request, err)
        if session is None:
            return invalid_credentials

        response = set_cognito_cookies(JsonResponse({'message': 'Login successful'}, status=200), tokens)
        response.data = {
            'jwt': tokens.access_token
        }
        return response

    def get(self, request):
        try:
            session = authenticate_request(request)
        except CognitoUnavailable:
            session = None
        return JsonResponse({'authenticated': session is not None}, status=200)

class RefreshView(APIView):
    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')
        session_expired = problem_response(request, 'session-expired', 'Your session has expired. Sign in again.')
        if not refresh_token:
            return session_expired

        try:
            access_token = get_cognito().refresh(refresh_token)
        except InvalidCredentials:
            return clear_auth_cookies(session_expired)
        except CognitoError as err:
            return _cognito_error_response(request, err)

        return set_access_cookie(JsonResponse({'message': 'Session refreshed'}, status=200), access_token)


class GoogleAuthView(APIView):
    def post(self, request):
        google_id_token = request_data(request).get('id_token')
        if not google_id_token:
            raise validation_problem([body_error('id_token', 'This field is required.')])

        try:
            identity = verify_google_id_token(google_id_token)
        except GoogleTokenError:
            return problem_response(request, 'invalid-google-token', 'The Google account could not be validated. Try again.')

        if not identity['email_verified']:
            return problem_response(request, 'google-email-unverified', 'Your Google email is not verified.')

        user = User.objects.filter(google_id=identity['sub']).first()
        if user is None:
            user = User.objects.filter(email__iexact=identity['email']).first()
            if user is not None:
                if user.google_id:
                    return problem_response(request, 'google-email-linked', 'This email is linked to another Google account.')
                user.google_id = identity['sub']
                user.save(update_fields=['google_id'])

        if user is not None:
            return set_session_cookie(JsonResponse({'status': 'authenticated'}, status=200), user)

        return JsonResponse({
            'status': 'signup_required',
            'signup_token': create_signup_token(identity['email'], identity['sub']),
            'prefill': {
                'email': identity['email'],
                'first_name': identity['given_name'],
                'last_name': identity['family_name'],
            },
        }, status=200)

class CepLookupThrottle(AnonRateThrottle):
    scope = 'cep_lookup'
    rate = '30/min'

class CepLookupView(APIView):
    throttle_classes = [CepLookupThrottle]

    def get(self, request, cep):
        try:
            return JsonResponse(lookup_cep(cep), status=200)
        except InvalidCep:
            return JsonResponse({'error': 'CEP inválido. Informe 8 dígitos.'}, status=400)
        except CepNotFound:
            return JsonResponse({'error': 'CEP não encontrado.'}, status=404)
        except CepServiceUnavailable:
            return JsonResponse({'error': 'Serviço de CEP indisponível. Preencha o endereço manualmente.'}, status=503)

class LogoutView(APIView):
    def post(self, request):
        refresh_token = request.COOKIES.get('refresh_token')
        if refresh_token:
            try:
                get_cognito().revoke(refresh_token)
            except CognitoError:
                pass  # the cookies are cleared either way; the failure is already logged by the service
        return clear_auth_cookies(JsonResponse({'message': 'User logged out'}, status=200))

class ChangePasswordView(APIView):
    
    def put(self, request):
        session, error = authenticated_user(request)
        if error:
            return error

        if session.provider != 'cognito':
            return problem_response(
                request, 'google-account-login', 'This account uses Google sign-in and has no password.'
            )

        data = json_object(request)
        errors = _string_field_errors(data, ['old_password', 'password'])
        if errors:
            raise validation_problem(errors)

        try:
            get_cognito().change_password(session.access_token, data['old_password'], data['password'])
        except InvalidCredentials:
            return problem_response(request, 'incorrect-current-password', 'The current password is incorrect.')
        except InvalidPassword:
            return problem_response(request, 'password-policy', PASSWORD_POLICY_DETAIL)
        except CognitoError as err:
            return _cognito_error_response(request, err)
        return JsonResponse({'message': 'Password updated successfully'}, status=200)
        
# 2 - The following views are related to the User Info
# Those views only works if cookies are present in the request       
# Therefore, they can be used only if the user is logged in and are user accessible

class UserInfoCookieView(APIView):
    def get(self, request):
        session, error = authenticated_user(request)
        if error:
            return error

        user = session.user
        if user.role == 'customer':
            customer = Customer.objects.filter(user=user).first()
            customer_data = CustomerSerializer(customer).data
            return JsonResponse({'customer': customer_data}, status=200)
        elif user.role == 'hairdresser':
            hairdresser = Hairdresser.objects.filter(user=user).first()
            hairdresser_data = HairdresserSerializer(hairdresser).data
            return JsonResponse({'hairdresser': hairdresser_data}, status=200)    
        else:
            return problem_response(request, 'internal-error', 'The account has an unsupported role.')

    def delete(self, request):
        session, error = authenticated_user(request)
        if error:
            return error

        return _delete_account(request, session.user)

    #This function does not handle password update procedure
    def put(self, request):
        session, error = authenticated_user(request)
        if error:
            return error

        user = session.user
        data = json_object(request)

        # The e-mail is the Cognito username, and changing it there needs a verification step.
        if 'email' in data and data['email'] != user.email:
            return problem_response(request, 'email-change-unsupported', 'Changing the email is not supported.')

        # Unlike sign-up, the phone here is the full stored number (55 included), as GET returns it.
        if 'phone' in data:
            data['phone'] = ''.join(ch for ch in str(data['phone']) if ch.isdigit())
            if User.objects.filter(phone=data['phone']).exclude(id=user.id).exists():
                return problem_response(request, 'phone-taken', PHONE_TAKEN_DETAIL)

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
        # Full personal data, so only for the account owner.
        session, error = authenticated_user(request)
        if error:
            return error
        if not is_own_email(session, email):
            return forbidden(request)

        user = session.user
        if (user.role == 'customer'):
            customer = Customer.objects.get(user=user)
            customer_serialized = CustomerSerializer(customer).data
            return JsonResponse({'data': customer_serialized}, status=200)
        else: 
            hairdresser = Hairdresser.objects.get(user=user)
            hairdresser_serialized = HairdresserSerializer(hairdresser).data
            return JsonResponse({'data': hairdresser_serialized}, status=200)

    
    def delete(self, request, email=None):
        # Only the account owner can delete it; the e-mail in the URL must be the session's.
        session, error = authenticated_user(request)
        if error:
            return error
        if not is_own_email(session, email):
            return forbidden(request)
        return _delete_account(request, session.user)

class CustomerHomeView(APIView):
    """
    API view for customer home page that returns:
    1. Hairdressers matching customer preferences in 'for_you' object
    2. 10 hairdressers for each of the specified preference categories
    """
    
    def get(self, request, email=None):
        for_you_data = []
        if email:
            # The "for you" section reveals the customer's preferences, so it is only for that customer.
            session, error = authenticated_user(request)
            if error:
                return error
            if not is_own_email(session, email):
                return forbidden(request)
            customer_user = session.user
            if customer_user.role != 'customer':
                return problem_response(request, 'customer-required', CUSTOMER_REQUIRED_DETAIL)
            customer_preferences = customer_user.preferences.all()
            
            # Get hairdressers matching customer preferences
            hairdressers_users = User.objects.filter(
                role='hairdresser',
                preferences__in=customer_preferences
            ).distinct()

            hairdressers_for_you = Hairdresser.objects.filter(user__in=hairdressers_users)
            
            # Prepare data for for_you response
            for_you_data = PublicHairdresserSerializer(hairdressers_for_you, many=True).data
        
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
                hairdressers_data = PublicHairdresserSerializer(hairdressers_per_preference, many=True).data
                
                preference_hairdressers[formated_preferences_name[i]] = hairdressers_data
            except Preferences.DoesNotExist:
                preference_hairdressers[formated_preferences_name[i]] = []
        
        # Prepare the final response
        response_data = {
            'for_you': for_you_data,
            'hairdressers_by_preferences': preference_hairdressers
        }     
        return JsonResponse(response_data, status=200)
    
class GeminiCompletionThrottle(AnonRateThrottle):
    scope = 'gemini_completion'
    rate = '10/hour'

class GeminiChatView(APIView):
    # Anonymous on purpose: the hairdresser sign-up calls it before the account exists.
    # The throttle caps the Gemini cost per IP.
    throttle_classes = [GeminiCompletionThrottle]

    def post(self, request):
        try:
            data = json.loads(request.body)
        except ValueError:
            data = None
        if not isinstance(data, dict):
            return JsonResponse({'error': 'Invalid request body'}, status=400)
        result = hairdresser_profile_ai_completion(data)
        return result
    
class HairdresserInfoView(APIView):
    def get(self,request,hairdresser_id=None): 
        try:
            hairdresser = Hairdresser.objects.get(id=hairdresser_id)
        except Hairdresser.DoesNotExist:
            return JsonResponse({'error': 'Hairdresser not found'}, status=404)

        hairdresser_serialized = PublicHairdresserSerializer(hairdresser).data
        return JsonResponse({'data': hairdresser_serialized}, status=200)