from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase
from opentelemetry.trace import StatusCode

from hairmatch import testing_telemetry
from hairmatch.ai_clients.gemini_client import generate_ai_text

PROMPT = 'Perfil de Maria Silva, telefone 92991234567, cabelo cacheado'
ANSWER = 'Maria Silva é especialista em cachos'


def model_answering(text=ANSWER, usage=(12, 7)):
    response = SimpleNamespace(text=text, usage_metadata=SimpleNamespace(prompt_token_count=usage[0], candidates_token_count=usage[1]))
    model = MagicMock()
    model.generate_content.return_value = response
    return model


class GenerateAiTextTelemetryTests(testing_telemetry.TelemetryMixin, SimpleTestCase):
    """TEL-25, TEL-26, TEL-27, TEL-58, TEL-59 for the profile description."""

    def requests(self):
        return sorted((a['feature'], a['outcome'], v) for a, v in self.points('hairmatch.ai.requests'))

    def tokens(self):
        return sorted((a['feature'], a['direction'], v) for a, v in self.points('hairmatch.ai.tokens'))

    def test_the_span_has_model_feature_and_token_counts_and_neither_prompt_nor_answer(self):
        with patch('hairmatch.ai_clients.gemini_client.genai.GenerativeModel', return_value=model_answering()):
            self.assertEqual(generate_ai_text(PROMPT), ANSWER)
        span = self.span('gemini generate_content')
        self.assertEqual(dict(span.attributes), {
            'gen_ai.request.model': 'gemini-2.0-flash', 'hairmatch.ai.feature': 'profile',
            'gen_ai.usage.input_tokens': 12, 'gen_ai.usage.output_tokens': 7,
        })
        text = repr(dict(span.attributes)) + span.name + repr(span.events) + repr(span.status.description)
        for private in ('Maria', '9299', 'cacheado', 'cachos'):
            self.assertNotIn(private, text)

    def test_the_counters_get_the_request_and_the_tokens(self):
        with patch('hairmatch.ai_clients.gemini_client.genai.GenerativeModel', return_value=model_answering()):
            generate_ai_text(PROMPT)
        self.assertEqual(self.requests(), [('profile', 'ok', 1)])
        self.assertEqual(self.tokens(), [('profile', 'input', 12), ('profile', 'output', 7)])

    def test_a_response_without_usage_counts_the_request_and_no_tokens(self):
        model = model_answering()
        model.generate_content.return_value = SimpleNamespace(text=ANSWER)
        with patch('hairmatch.ai_clients.gemini_client.genai.GenerativeModel', return_value=model):
            generate_ai_text(PROMPT)
        span = self.span('gemini generate_content')
        self.assertNotIn('gen_ai.usage.input_tokens', span.attributes)
        self.assertEqual(self.requests(), [('profile', 'ok', 1)])
        self.assertEqual(self.tokens(), [])

    def test_a_failing_call_marks_the_span_with_the_type_counts_error_and_the_exception_goes_on(self):
        model = MagicMock()
        model.generate_content.side_effect = TimeoutError(f'deadline exceeded for {PROMPT}')
        with patch('hairmatch.ai_clients.gemini_client.genai.GenerativeModel', return_value=model):
            with self.assertRaises(TimeoutError):
                generate_ai_text(PROMPT)
        span = self.span('gemini generate_content')
        self.assertEqual(span.status.status_code, StatusCode.ERROR)
        self.assertEqual(span.attributes['error.type'], 'TimeoutError')
        self.assertNotIn('Maria', repr(span.status.description) + repr(span.events) + repr(dict(span.attributes)))
        self.assertEqual(self.requests(), [('profile', 'error', 1)])
        self.assertEqual(self.tokens(), [])

    def test_an_answer_that_cannot_be_read_counts_error(self):
        class Blocked:
            usage_metadata = None

            @property
            def text(self):
                raise ValueError('the response has no valid Part')

        model = MagicMock()
        model.generate_content.return_value = Blocked()
        with patch('hairmatch.ai_clients.gemini_client.genai.GenerativeModel', return_value=model):
            with self.assertRaises(ValueError):
                generate_ai_text(PROMPT)
        self.assertEqual(self.requests(), [('profile', 'error', 1)])

    def test_the_chatbot_label_is_passed_through(self):
        with patch('hairmatch.ai_clients.gemini_client.genai.GenerativeModel', return_value=model_answering()):
            generate_ai_text(PROMPT, feature='chatbot')
        self.assertEqual(self.requests(), [('chatbot', 'ok', 1)])
