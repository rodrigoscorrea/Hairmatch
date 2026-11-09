"""
TEL-49: no personal data reaches the telemetry (#194). Each covered flow runs with the personal data below, and
everything the backend would export afterwards (`testing_telemetry.corpus`) is searched for it. The sign-up and the
login talk to the Cognito fake here; their botocore leg is proved against the real stack in the E2E (T32).
"""
import json
from unittest.mock import MagicMock, PropertyMock, patch

import requests
from django.core.cache import cache
from django.test import TestCase, TransactionTestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from hairmatch import testing_telemetry
from hairmatch.image_fixtures import make_upload
from notifications.models import PushDevice
from notifications.sns import SnsService
from notifications.tests.helpers import login as session_client
from notifications.tests.test_dispatch_telemetry import ARN, TOKEN, ReserveFixture
from users.models import User
from users.testing import activate_account
from users.tests import GalleryApiTestCase, _register_payload

FIRST, LAST = 'Zuleica', 'Sentinela'
EMAIL = 'zuleica.sentinela@privado.example.org'
PHONE = '92987654321'
CPF = '52998224725'
CNPJ = '11222333000181'
CEP = '69987654'
ADDRESS = 'Rua Sentinela Secreta'
NEIGHBORHOOD = 'Bairro Sentinela'
PASSWORD = 'SenhaSentinela9'
PHOTO_NAME = 'foto-sentinela-privada'

# What must not appear, in the forms it takes in a log line or an URL.
PERSONAL_DATA = (
    FIRST, LAST, EMAIL, 'zuleica.sentinela', '987654321', '98765-4321', CPF, '529.982.247-25', CNPJ, '11.222.333/0001-81',
    CEP, '69987-654', ADDRESS, NEIGHBORHOOD, PASSWORD, PHOTO_NAME, TOKEN, 'secret-endpoint', ARN,
)


class PrivacyMixin(testing_telemetry.TelemetryMixin):
    def assert_nothing_personal_exported(self, minimum_spans=1):
        exported = testing_telemetry.corpus()
        self.assertGreaterEqual(len(self.spans()), minimum_spans, 'the flow must leave spans, or the search proves nothing')
        for value in PERSONAL_DATA:
            with self.subTest(value=value):
                self.assertNotIn(value, exported)


def personal_payload(**overrides):
    return _register_payload(
        first_name=FIRST, last_name=LAST, email=EMAIL, phone=PHONE, cpf=CPF, address=ADDRESS,
        neighborhood=NEIGHBORHOOD, postal_code=CEP, password=PASSWORD, **overrides,
    )


class SignupAndLoginPrivacyTests(PrivacyMixin, TestCase):
    def test_signup_with_a_hairdresser_leaves_no_personal_data(self):
        payload = personal_payload(role='hairdresser', cnpj=CNPJ, experience_time='5', experiences='x', products='y', resume='z')
        payload.pop('cpf')
        testing_telemetry.clear()
        response = APIClient().post(reverse('register'), data=payload)
        self.assertEqual(response.status_code, 201)
        self.assert_nothing_personal_exported()

    def test_signup_of_a_customer_leaves_no_personal_data(self):
        testing_telemetry.clear()
        self.assertEqual(APIClient().post(reverse('register'), data=personal_payload()).status_code, 201)
        self.assert_nothing_personal_exported()

    def test_login_leaves_no_personal_data_on_success_and_on_a_wrong_password(self):
        client = APIClient()
        client.post(reverse('register'), data=personal_payload())
        activate_account(EMAIL)
        testing_telemetry.clear()
        for password, expected in ((PASSWORD, 200), ('outra-senha-errada', 401), (PASSWORD, 200)):
            response = client.post(
                reverse('login'), data=json.dumps({'email': EMAIL, 'password': password}), content_type='application/json',
            )
            self.assertEqual(response.status_code, expected)
        self.assert_nothing_personal_exported()


class CepPrivacyTests(PrivacyMixin, TestCase):
    def setUp(self):
        super().setUp()
        cache.clear()

    def providers(self, viacep, brasilapi):
        answers = {'viacep.com.br': viacep, 'brasilapi.com.br': brasilapi}

        def send(adapter, request, **kwargs):
            result = answers[request.url.split('/')[2]]
            if isinstance(result, Exception):
                raise result
            response = requests.Response()
            response.status_code = result[0]
            response._content = json.dumps(result[1]).encode()
            response.url, response.request = request.url, request
            return response

        return patch('requests.adapters.HTTPAdapter.send', send)

    def test_a_lookup_that_succeeds_leaves_the_cep_and_the_address_out(self):
        found = {'logradouro': ADDRESS, 'bairro': NEIGHBORHOOD, 'localidade': 'Manaus', 'uf': 'AM'}
        with self.providers((200, found), (200, {})):
            response = self.client.get(f'/api/postal-codes/{CEP}', HTTP_X_FORWARDED_FOR='10.1.2.3')
        self.assertEqual(response.status_code, 200)
        self.assert_nothing_personal_exported()

    def test_a_lookup_that_fails_in_both_providers_leaves_the_cep_out_of_the_error_text(self):
        down = requests.ConnectionError(
            f"HTTPSConnectionPool(host='viacep.com.br', port=443): Max retries exceeded with url: /ws/{CEP}/json/ (Caused by X)"
        )
        slow = requests.ConnectTimeout(
            f"HTTPSConnectionPool(host='brasilapi.com.br', port=443): Max retries exceeded with url: /api/cep/v2/{CEP} (Caused by Y)"
        )
        with self.providers(down, slow):
            response = self.client.get(f'/api/postal-codes/{CEP}')
        self.assertEqual(response.status_code, 503)
        self.assert_nothing_personal_exported()

    def test_the_preflight_of_the_lookup_leaves_the_cep_out(self):
        response = self.client.options(
            f'/api/postal-codes/{CEP}', HTTP_ORIGIN='http://localhost:8081',
            HTTP_ACCESS_CONTROL_REQUEST_METHOD='GET', HTTP_ACCESS_CONTROL_REQUEST_HEADERS='traceparent',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Access-Control-Allow-Origin'], 'http://localhost:8081')
        self.assert_nothing_personal_exported()


class ReservePushPrivacyTests(PrivacyMixin, ReserveFixture, TransactionTestCase):
    def test_a_reservation_with_a_push_leaves_no_personal_data(self):
        User.objects.filter(pk=self.customer_user.pk).update(
            first_name=FIRST, last_name=LAST, email=EMAIL, phone=PHONE, address=ADDRESS, neighborhood=NEIGHBORHOOD,
            postal_code=CEP,
        )
        self.customer_user.refresh_from_db()
        self.stubber.add_response('publish', {'MessageId': 'm-1'})
        testing_telemetry.clear()
        with self.stubber:
            response = self.post_reservation()
        self.assertEqual(response.status_code, 201)
        self.assertTrue(PushDevice.objects.filter(token=TOKEN).exists())
        self.assert_nothing_personal_exported(minimum_spans=3)

    def test_a_push_that_fails_leaves_no_personal_data_in_the_error_text(self):
        User.objects.filter(pk=self.customer_user.pk).update(first_name=FIRST, last_name=LAST)
        self.stubber.add_client_error(
            'publish', service_error_code='InternalError', http_status_code=500,
            # What an error can quote: the endpoint (an ARN), and the e-mail and phone of the user.
            service_message=f'endpoint {ARN} of {EMAIL} and {PHONE} is not reachable',
        )
        testing_telemetry.clear()
        with self.stubber, self.assertLogs('notifications', 'WARNING'):
            self.assertEqual(self.post_reservation().status_code, 201)
        self.assert_nothing_personal_exported(minimum_spans=3)


@override_settings(
    STORAGES={
        'default': {'BACKEND': 'hairmatch.storage.S3MediaStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    },
    S3_BUCKET_NAME='media-bucket',
)
class UploadPrivacyTests(PrivacyMixin, GalleryApiTestCase):
    def test_a_photo_upload_leaves_the_file_name_and_key_out(self):
        client, stubber = testing_telemetry.stubbed_client('s3')
        stubber.add_client_error('head_object', service_error_code='404', http_status_code=404)
        stubber.add_response('put_object', {})
        testing_telemetry.clear()
        with patch('hairmatch.storage.S3MediaStorage.client', new_callable=PropertyMock, return_value=client), stubber:
            response = self._post(make_upload(f'{PHOTO_NAME}.png', size=(300, 200), fmt='PNG'))
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.span('S3.PutObject').attributes['rpc.method'], 'PutObject')
        self.assert_nothing_personal_exported(minimum_spans=3)


class GeminiPrivacyTests(PrivacyMixin, TestCase):
    def test_the_profile_generation_leaves_the_profile_and_the_text_out(self):
        model = MagicMock()
        model.generate_content.return_value = MagicMock(text=f'{FIRST} {LAST} corta cabelos em {NEIGHBORHOOD}', usage_metadata=None)
        body = json.dumps({
            'first_name': FIRST, 'last_name': LAST, 'email': EMAIL, 'phone': PHONE, 'address': ADDRESS,
            'neighborhood': NEIGHBORHOOD, 'cnpj': CNPJ, 'preferences': [],
        })
        testing_telemetry.clear()
        with patch('hairmatch.ai_clients.gemini_client.genai.GenerativeModel', return_value=model), \
                patch('hairmatch.ai_clients.gemini_client.setup_environment'):
            response = self.client.post(reverse('gemini_completion'), data=body, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        calls = [s for s in self.spans() if s.name == 'gemini generate_content']
        self.assertEqual([s.attributes['hairmatch.ai.feature'] for s in calls], ['profile', 'profile'])  # two prompts per profile
        self.assert_nothing_personal_exported()

    def test_a_generation_that_fails_leaves_the_masked_data_out_of_the_error_text(self):
        model = MagicMock()
        # What an error can quote of the prompt: the e-mail, the phone and the CPF, which the redaction masks.
        model.generate_content.side_effect = RuntimeError(f'blocked prompt with {EMAIL}, {PHONE} and {CPF}')
        testing_telemetry.clear()
        with patch('hairmatch.ai_clients.gemini_client.genai.GenerativeModel', return_value=model), \
                patch('hairmatch.ai_clients.gemini_client.setup_environment'):
            response = self.client.post(
                reverse('gemini_completion'), data=json.dumps({'first_name': FIRST, 'preferences': []}),
                content_type='application/json',
            )
        self.assertEqual(response.status_code, 503)
        self.assert_nothing_personal_exported()
