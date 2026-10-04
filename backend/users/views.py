from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import User, Customer, Hairdresser
from hairmatch.images import InvalidImage
from preferences.models import Preferences
import json
import logging
import re
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Q, Count
from .serializers import UserSerializer, CustomerSerializer, HairdresserSerializer, HairdresserFullInfoSerializer, PublicHairdresserSerializer
from hairmatch.ai_clients.gemini_client import hairdresser_profile_ai_completion
from .filters import HairdresserFilter
from .serializers import SearchResultSerializer # Import our new serializer
from .filters import HairdresserFilter
from service.models import Service
from agenda.models import Agenda
from reserve.models import Reserve
from reserve.views import cancel_reserve
from review.models import Review
from itertools import chain
from rest_framework.parsers import MultiPartParser, FormParser
from preferences.models import Preferences
from django.core.files.storage import default_storage
from django.db import connection, transaction
from .auth_tokens import set_session_cookie, set_cognito_cookies, set_access_cookie, clear_auth_cookies, create_signup_token, decode_signup_token, InvalidSignupToken
from .authentication import (
    CUSTOMER_REQUIRED_DETAIL,
    authenticate_request,
    authenticate_token,
    authenticated_user,
)
from .cognito import (
    AlreadyConfirmed,
    CognitoError,
    CognitoUnavailable,
    ExpiredConfirmationCode,
    InvalidConfirmationCode,
    InvalidCredentials,
    InvalidPassword,
    TooManyRequests,
    UserAlreadyExists,
    UserNotConfirmed,
    get_cognito,
)
from .throttles import (
    ConfirmEmailThrottle,
    ConfirmIpThrottle,
    RegisterEmailThrottle,
)
from .google_auth import verify_google_id_token, GoogleTokenError
from .cep_lookup import lookup_cep, InvalidCep, CepNotFound, CepServiceUnavailable
from rest_framework.throttling import AnonRateThrottle
from hairmatch.problems import (
    Problem,
    body_error,
    is_id_list,
    json_object,
    missing_field_errors,
    problem_response,
    request_data,
    validation_problem,
)

logger = logging.getLogger(__name__)

GOOGLE_SIGNUP_REQUIRED_FIELDS = [
    'first_name', 'last_name', 'phone', 'address',
    'neighborhood', 'city', 'state', 'postal_code',
]
ROLE_DOCUMENT_FIELD = {'customer': 'cpf', 'hairdresser': 'cnpj'}
PASSWORD_POLICY_DETAIL = 'The password must have at least 8 characters, with an uppercase letter, a lowercase letter and a number.'
PHONE_TAKEN_DETAIL = 'This phone number is already registered.'
EMAIL_TAKEN_DETAIL = 'This email is already registered.'
INVALID_PROFILE_PICTURE_DETAIL = 'The profile picture is not a valid image.'
ACCOUNT_NOT_CREATED_DETAIL = 'The account could not be created.'
EMAIL_NOT_CONFIRMED_DETAIL = 'Confirm your email with the code we sent to sign in.'
CONFIRMATION_CODE_PATTERN = re.compile(r'[0-9]{6}')


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
    """
    Deletes the user's rows and then the Cognito user (e-mail accounts), all or nothing, and clears the
    session cookies. The stored pictures go once the deletion is committed.
    """
    email, cognito_sub = user.email, user.cognito_sub
    try:
        with transaction.atomic():
            pictures = _delete_account_rows(user)
            # The foreign keys are checked at commit: check them now, before Cognito is touched.
            connection.check_constraints()
            if cognito_sub:
                get_cognito().admin_delete_user(email)
            transaction.on_commit(lambda: _delete_stored_files(pictures))
    except CognitoError as err:
        return _cognito_error_response(request, err)
    return clear_auth_cookies(HttpResponse(status=204))


def _delete_account_rows(user):
    """
    Deletes the user and every row that points at them, and returns the storage names of their pictures.
    Their reservations are cancelled, as a customer and as a hairdresser: the customers of a hairdresser
    who leaves are not notified yet (#171).
    """
    reserves = Reserve.objects.filter(
        Q(customer__user=user) | Q(service__hairdresser__user=user)
    ).select_related('service')
    for reserve in reserves:
        cancel_reserve(reserve)
    Agenda.objects.filter(hairdresser__user=user).delete()
    Service.objects.filter(hairdresser__user=user).delete()

    # Reviews written and received go with the profiles (CASCADE); their pictures stay in storage otherwise.
    pictures = [
        name for name in Review.objects.filter(
            Q(customer__user=user) | Q(hairdresser__user=user)
        ).values_list('picture', flat=True) if name
    ]
    if user.profile_picture:
        pictures.append(user.profile_picture.name)
    user.delete()
    return pictures


def _delete_stored_files(names):
    for name in names:
        try:
            default_storage.delete(name)
        except Exception:
            logger.exception('Could not delete %s from the media storage', name)


# An e-mail account that never confirmed its address: it holds its e-mail and phone for no one.
_PENDING_ACCOUNT = Q(is_active=False, cognito_sub__isnull=False)


def _pending_accounts(email=None, phone=None):
    """The pending accounts that hold this e-mail (any case) or this stored phone."""
    holders = Q(pk__in=[])
    if email:
        holders |= Q(email__iexact=email)
    if phone:
        holders |= Q(phone=phone)
    return User.objects.filter(_PENDING_ACCOUNT, holders)


def _replace_pending_accounts(email, phone=None):
    """Replaces every pending account holding this e-mail or phone. Raises CognitoError, leaving the rest untouched."""
    for pending in _pending_accounts(email, phone):
        _replace_pending_account(pending)


def _replace_pending_account(user):
    """
    Deletes a pending account in Cognito and then in Postgres, so a Cognito outage leaves both untouched.
    Raises CognitoError when Cognito cannot delete the user.
    """
    get_cognito().admin_delete_user(user.email)
    user.delete()


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

class RegisterThrottle(AnonRateThrottle):
    scope = 'register'
    rate = '10/hour'


class LoginThrottle(AnonRateThrottle):
    # Cognito has its own lockout; this caps the password guesses that reach it from one IP.
    scope = 'login'
    rate = '10/min'


# 1 - The following views are related to user authentication procedures
class RegisterView(APIView):
    parser_classes = (MultiPartParser, FormParser)
    # Per IP against sweeps, per e-mail against spam to one inbox: each sign-up sends a verification e-mail.
    throttle_classes = [RegisterThrottle, RegisterEmailThrottle]

    def post(self, request):
        data = request_data(request)
        if data.get('google_signup_token'):
            return self._register_with_google(request, data)

        errors = missing_field_errors(data, ['role', 'email', 'password', 'phone'])
        errors += _role_and_phone_errors(data)
        if errors:
            raise validation_problem(errors)

        email = data['email']
        role = data['role']
        phone = data['phone']
        stored_phone = normalize_phone(phone)
        if User.objects.filter(email__iexact=email).exclude(_PENDING_ACCOUNT).exists():
            return problem_response(request, 'email-taken', EMAIL_TAKEN_DETAIL)
        if User.objects.filter(phone=stored_phone).exclude(_PENDING_ACCOUNT).exists():
            return problem_response(request, 'phone-taken', PHONE_TAKEN_DETAIL)

        try:
            _replace_pending_accounts(email, stored_phone)
            cognito_sub = self._sign_up(email, data['password'])
        except InvalidPassword:
            return problem_response(request, 'password-policy', PASSWORD_POLICY_DETAIL)
        except UserAlreadyExists:
            return problem_response(request, 'email-taken', EMAIL_TAKEN_DETAIL)
        except CognitoError as err:
            return _cognito_error_response(request, err)

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
                    cognito_sub=cognito_sub,
                    role=role,
                    # Pending until the e-mailed code is confirmed (POST /api/auth/email-confirmations).
                    is_active=False,
                )

                if 'profile_picture' in request.FILES:
                    user.profile_picture = request.FILES['profile_picture']
                    user.save()

                _create_role_profile(user, data)
        except InvalidImage:
            failure = problem_response(request, 'invalid-image', INVALID_PROFILE_PICTURE_DETAIL)
        except Problem as problem:
            failure = problem_response(request, problem.slug, problem.detail, problem.errors)
        except Exception:
            logger.exception('E-mail sign-up failed')
            failure = problem_response(request, 'internal-error', ACCOUNT_NOT_CREATED_DETAIL)
        else:
            return JsonResponse(
                {'message': f"{role} user registered successfully", 'confirmation_required': True}, status=201
            )

        _discard_cognito_user(email)
        return failure

    @staticmethod
    def _sign_up(email, password):
        """
        SignUp, retried once when the pool still holds an UNCONFIRMED user nobody here owns (a sign-up
        whose rows were lost). Any other user in the pool keeps the e-mail taken.
        """
        cognito = get_cognito()
        try:
            return cognito.sign_up(email, password)
        except UserAlreadyExists:
            if cognito.admin_get_status(email) != 'UNCONFIRMED':
                raise
            cognito.admin_delete_user(email)
            return cognito.sign_up(email, password)

    def _register_with_google(self, request, data):
        try:
            claims = decode_signup_token(data.get('google_signup_token'))
        except InvalidSignupToken:
            return problem_response(
                request, 'signup-session-expired', 'Your Google sign-up session has expired. Sign in with Google again.'
            )

        role = data.get('role')
        required = list(GOOGLE_SIGNUP_REQUIRED_FIELDS)
        if role in ROLE_DOCUMENT_FIELD:
            required.append(ROLE_DOCUMENT_FIELD[role])
        errors = missing_field_errors(data, ['role'] + required)
        errors += _role_and_phone_errors(data)
        if errors:
            raise validation_problem(errors)

        phone = data['phone']
        # The e-mail comes from the signup token; form email/password fields are ignored.
        email = claims['email']
        google_id = claims['sub']
        stored_phone = normalize_phone(phone)
        if User.objects.filter(email__iexact=email).exclude(_PENDING_ACCOUNT).exists():
            return problem_response(request, 'email-taken', EMAIL_TAKEN_DETAIL)
        if User.objects.filter(google_id=google_id).exists():
            return problem_response(request, 'google-account-taken', 'This Google account is already registered.')
        if User.objects.filter(phone=stored_phone).exclude(_PENDING_ACCOUNT).exists():
            return problem_response(request, 'phone-taken', PHONE_TAKEN_DETAIL)

        # Google proved the e-mail, so a pending account that holds it or the phone is replaced, never inherited.
        try:
            _replace_pending_accounts(email, stored_phone)
        except CognitoError as err:
            return _cognito_error_response(request, err)

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
                )
                if 'profile_picture' in request.FILES:
                    user.profile_picture = request.FILES['profile_picture']
                    user.save()
                _create_role_profile(user, data)
        except InvalidImage:
            return problem_response(request, 'invalid-image', INVALID_PROFILE_PICTURE_DETAIL)
        except Problem as problem:
            return problem_response(request, problem.slug, problem.detail, problem.errors)
        except Exception:
            logger.exception('Google sign-up failed')
            return problem_response(request, 'internal-error', ACCOUNT_NOT_CREATED_DETAIL)

        return set_session_cookie(JsonResponse({'message': f"{role} user registered successfully"}, status=201), user)


def _role_and_phone_errors(data):
    """`errors` items for a role outside the two accounts and a phone too short. A missing field is reported elsewhere."""
    errors = []
    role = data.get('role')
    if role and role not in ROLE_DOCUMENT_FIELD:
        errors.append(body_error('role', 'The role must be customer or hairdresser.'))
    phone = data.get('phone')
    if phone and len(phone) < 10:
        errors.append(body_error('phone', 'The phone number is too short.'))
    return errors


def _create_role_profile(user, data):
    # Raises Problem('validation-error') when preferences is not a JSON list of ids.
    try:
        preferences_ids = json.loads(data.get('preferences', '[]'))
    except (TypeError, ValueError):
        preferences_ids = None
    if not is_id_list(preferences_ids):
        raise validation_problem([body_error('preferences', 'The preferences must be a JSON list of ids.')])
    if len(preferences_ids) > 0:
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
    throttle_classes = [LoginThrottle]

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
        email_not_confirmed = problem_response(request, 'email-not-confirmed', EMAIL_NOT_CONFIRMED_DETAIL)
        try:
            tokens = get_cognito().authenticate(email, password)
            # A pool that lets an UNCONFIRMED user sign in (the local emulator) must not open a session for it.
            if _pending_accounts(email).exists():
                return email_not_confirmed
            session = authenticate_token(tokens.access_token)
        except UserNotConfirmed:
            return email_not_confirmed
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


class EmailConfirmationView(APIView):
    throttle_classes = [ConfirmIpThrottle, ConfirmEmailThrottle]

    def post(self, request):
        data = request_data(request)
        errors = _string_field_errors(data, ['email', 'code'])
        code = data.get('code')
        if isinstance(code, str) and code and not CONFIRMATION_CODE_PATTERN.fullmatch(code):
            errors.append(body_error('code', 'The code must have 6 digits.'))
        if errors:
            raise validation_problem(errors)

        confirmed = JsonResponse({'message': 'Email confirmed'}, status=200)
        # An unknown e-mail answers like a wrong code, so this route does not tell which accounts exist.
        invalid_code = problem_response(request, 'invalid-confirmation-code', 'The confirmation code is invalid.')
        user = User.objects.filter(email__iexact=data['email'].strip(), cognito_sub__isnull=False).first()
        if user is None:
            return invalid_code
        if user.is_active:
            return confirmed

        try:
            get_cognito().confirm_sign_up(user.email, code)
        except AlreadyConfirmed:
            pass  # confirmed in the pool earlier; only the database is behind
        except InvalidConfirmationCode:
            return invalid_code
        except ExpiredConfirmationCode:
            return problem_response(
                request, 'confirmation-code-expired', 'The confirmation code has expired. Request a new one.'
            )
        except CognitoError as err:
            return _cognito_error_response(request, err)

        user.is_active = True
        user.save(update_fields=['is_active'])
        return confirmed


class SessionView(APIView):
    """Whether the request carries a valid session. Never 401: the app asks it before it knows."""

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
            # A pending account is never linked: the person who typed that e-mail may not own it.
            try:
                _replace_pending_accounts(identity['email'])
            except CognitoError as err:
                return _cognito_error_response(request, err)
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
            return problem_response(request, 'invalid-postal-code', 'The postal code must have 8 digits.')
        except CepNotFound:
            return problem_response(request, 'postal-code-not-found', 'No address was found for this postal code.')
        except CepServiceUnavailable:
            return problem_response(
                request, 'postal-code-service-unavailable', 'The postal code providers are unavailable.'
            )

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

class CurrentUserView(APIView):
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
    def patch(self, request):
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

        # The rating is not the user's to set: it is the public score hairdressers are ranked by.
        allowed_fields = [
            'first_name', 'last_name', 'phone', 'email',
            'address', 'number', 'postal_code',
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
        query = request.query_params.get('q', None)

        if not query:
            return JsonResponse({'data': []}, status=200)

        hairdresser_queryset = Hairdresser.objects.all()
        hairdresser_filter = HairdresserFilter({'search': query}, queryset=hairdresser_queryset)
        hairdresser_results = hairdresser_filter.qs

        service_results = Service.objects.filter(
            Q(name__icontains=query)
        ) 
        combined_results = list(chain(hairdresser_results, service_results))
        serializer = SearchResultSerializer(combined_results, many=True, context={'request': request})

        return JsonResponse({'data':serializer.data}, status=200)

def _home_response(for_you_data):
    """The home body: the 'for_you' list plus 10 hairdressers for each of the specified preference categories."""
    specific_preferences = ["Coloração", "Cachos", "Barbearia", "Tranças"]
    formated_preferences_name = ["coloracao", "cachos", "barbearia", "trancas"]
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

    return JsonResponse({
        'for_you': for_you_data,
        'hairdressers_by_preferences': preference_hairdressers
    }, status=200)


class HomeView(APIView):
    """The public home: the preference categories and no 'for_you' section."""

    def get(self, request):
        return _home_response([])


class CustomerHomeView(APIView):
    """The home of the logged customer: hairdressers matching their preferences in 'for_you', plus the categories."""

    def get(self, request):
        # The "for you" section reveals the customer's preferences, so it is only for that customer.
        session, error = authenticated_user(request)
        if error:
            return error
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

        return _home_response(PublicHairdresserSerializer(hairdressers_for_you, many=True).data)

class GeminiCompletionThrottle(AnonRateThrottle):
    scope = 'gemini_completion'
    rate = '10/hour'

class GeminiChatView(APIView):
    # Anonymous on purpose: the hairdresser sign-up calls it before the account exists.
    # The throttle caps the Gemini cost per IP.
    throttle_classes = [GeminiCompletionThrottle]

    def post(self, request):
        return hairdresser_profile_ai_completion(json_object(request))
    
class HairdresserInfoView(APIView):
    def get(self,request,hairdresser_id=None): 
        try:
            hairdresser = Hairdresser.objects.get(id=hairdresser_id)
        except Hairdresser.DoesNotExist:
            return problem_response(request, 'not-found', 'Hairdresser not found.')

        hairdresser_serialized = PublicHairdresserSerializer(hairdresser).data
        return JsonResponse({'data': hairdresser_serialized}, status=200)