import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from hairmatch.redaction import REPLACEMENTS, redact, sanitize_text, scrub_arns, scrub_urls

JWT = 'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ1c2VyQGV4YW1wbGUuY29tIn0.c2lnbmF0dXJlLXZhbHVl'
COLLECTOR_CONFIG = Path(settings.BASE_DIR).parent / 'docker' / 'observability' / 'otel' / 'config.yaml'


class RedactTests(SimpleTestCase):
    """TEL-44: the message is redacted with the Collector's patterns, in the Collector's order."""

    def test_replaces_each_kind_of_personal_data_by_its_marker(self):
        cases = {
            'login of maria.silva+x@example.com.br failed': 'login of [email] failed',
            f'token {JWT} rejected': 'token [jwt] rejected',
            'cpf 123.456.789-09 invalid': 'cpf [cpf] invalid',
            'cpf 12345678909 invalid': 'cpf [cpf] invalid',
            'cnpj 12.345.678/0001-95 invalid': 'cnpj [cnpj] invalid',
            'cnpj 12345678000195 invalid': 'cnpj [cnpj] invalid',
            'phone (92) 99999-9999 invalid': 'phone [telefone] invalid',
            'phone +55 92 99999-9999 invalid': 'phone [telefone] invalid',
            'phone 92 3234-5678 invalid': 'phone [telefone] invalid',
        }
        for text, expected in cases.items():
            with self.subTest(text=text):
                self.assertEqual(redact(text), expected)

    def test_whatsapp_number_becomes_a_phone_marker_not_an_email_marker(self):
        self.assertEqual(redact('from 5592999999999@s.whatsapp.net now'), 'from [telefone] now')

    def test_jwt_is_replaced_whole_before_the_email_rule_sees_its_pieces(self):
        self.assertEqual(redact(JWT), '[jwt]')

    def test_text_without_personal_data_is_unchanged(self):
        text = 'GET api/hairdressers/<int:hairdresser_id>/gallery-photos 200 in 12 ms'
        self.assertEqual(redact(text), text)

    def test_ids_stay_when_they_are_short(self):
        self.assertEqual(redact('reserve 4821 of hairdresser 77'), 'reserve 4821 of hairdresser 77')

    def test_long_digit_sequence_is_masked_even_when_it_is_not_personal_data(self):
        """A documented false positive: the safe side, as in the Collector."""
        self.assertEqual(redact('epoch 1700000000 s'), 'epoch [telefone] s')

    def test_several_values_in_one_message_are_all_replaced(self):
        out = redact('a@b.co 123.456.789-09 (92) 99999-9999')
        self.assertEqual(out, '[email] [cpf] [telefone]')

    def test_order_of_the_markers_is_jwt_whatsapp_email_cnpj_cpf_phone(self):
        self.assertEqual(
            [marker for _, marker in REPLACEMENTS],
            ['[jwt]', '[telefone]', '[email]', '[cnpj]', '[cpf]', '[telefone]'],
        )


class CollectorParityTests(SimpleTestCase):
    """TEL-44: the five expressions are the ones in docker/observability/otel/config.yaml."""

    def test_patterns_match_the_collector_config(self):
        self.assertTrue(COLLECTOR_CONFIG.is_file(), COLLECTOR_CONFIG)
        text = COLLECTOR_CONFIG.read_text(encoding='utf-8')
        found = re.findall(r'replace_pattern\(body, "(.+?)", "(\[\w+\])"\) where IsString\(body\)', text)
        collector = [(pattern.replace('\\\\', '\\'), marker) for pattern, marker in found]
        self.assertEqual(len(collector), 5)
        app = [(p.pattern, m) for p, m in REPLACEMENTS if p.pattern != r'\d+@s\.whatsapp\.net']
        self.assertEqual(app, collector)


class CepPathTests(SimpleTestCase):
    def test_the_cep_of_the_postal_code_path_is_masked_in_every_form_django_logs_it(self):
        for text, expected in (
            ('Not Found: /api/postal-codes/69000000', 'Not Found: /api/postal-codes/{cep}'),
            ('Service Unavailable: /api/postal-codes/69000-000', 'Service Unavailable: /api/postal-codes/{cep}'),
            ('"GET /api/postal-codes/69000000 HTTP/1.1" 200', '"GET /api/postal-codes/{cep} HTTP/1.1" 200'),
            ('Bad Request: /api/postal-codes/abc', 'Bad Request: /api/postal-codes/{cep}'),
        ):
            with self.subTest(text=text):
                self.assertEqual(redact(text), expected)

    def test_other_paths_are_left_alone(self):
        self.assertEqual(redact('Conflict: /api/hairdressers/12/gallery-photos'), 'Conflict: /api/hairdressers/12/gallery-photos')


class ScrubTests(SimpleTestCase):
    def test_url_keeps_scheme_and_host_and_drops_path_and_query(self):
        self.assertEqual(
            scrub_urls('GET https://viacep.com.br/ws/69000000/json/?x=1 failed'),
            'GET https://viacep.com.br/[path] failed',
        )

    def test_url_without_path_is_unchanged(self):
        self.assertEqual(scrub_urls('call to http://localstack:4566 refused'), 'call to http://localstack:4566 refused')

    def test_the_bare_path_of_a_urllib3_connection_error_is_dropped(self):
        text = (
            "HTTPSConnectionPool(host='viacep.com.br', port=443): Max retries exceeded with url: /ws/69000000/json/ "
            "(Caused by NewConnectionError('x'))"
        )
        self.assertEqual(
            scrub_urls(text),
            "HTTPSConnectionPool(host='viacep.com.br', port=443): Max retries exceeded with url: /[path] "
            "(Caused by NewConnectionError('x'))",
        )

    def test_arn_is_replaced(self):
        self.assertEqual(
            scrub_arns("No endpoint for 'arn:aws:sns:us-east-2:000000000000:endpoint/GCM/app/abc-123'"),
            "No endpoint for '[arn]'",
        )

    def test_sanitize_text_applies_urls_arns_and_personal_data(self):
        out = sanitize_text('https://x.com/a/b arn:aws:sns:r:1:e/f user@example.com')
        self.assertEqual(out, 'https://x.com/[path] [arn] [email]')
