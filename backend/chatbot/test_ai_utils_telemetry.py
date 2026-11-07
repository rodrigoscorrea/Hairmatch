from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import requests
from django.test import TestCase
from opentelemetry.trace import StatusCode

from chatbot.ai_utils import AiUtils
from hairmatch import testing_telemetry

CONVERSATION = 'Maria Silva, 92991234567, quer luzes'


def history():
    return [MagicMock(parts=[MagicMock(text=CONVERSATION)])]


def model_answering(text='luzes', usage=(30, 3)):
    model = MagicMock()
    model.generate_content.return_value = SimpleNamespace(
        text=text, usage_metadata=SimpleNamespace(prompt_token_count=usage[0], candidates_token_count=usage[1]),
    )
    return model


class AiUtilsTelemetryTests(testing_telemetry.TelemetryMixin, TestCase):
    """TEL-25 to TEL-27, TEL-41, TEL-42, TEL-58 for the chatbot helpers."""

    def requests_counted(self):
        return sorted((a['feature'], a['outcome'], v) for a, v in self.points('hairmatch.ai.requests'))

    def test_the_preference_extraction_is_a_chatbot_gemini_span_with_tokens_and_no_conversation(self):
        with patch('chatbot.ai_utils.genai.GenerativeModel', return_value=model_answering()):
            self.assertEqual(AiUtils.extract_preferences_from_conversation(history()), ['luzes'])
        span = self.span('gemini generate_content')
        self.assertEqual(span.attributes['hairmatch.ai.feature'], 'chatbot')
        self.assertEqual((span.attributes['gen_ai.usage.input_tokens'], span.attributes['gen_ai.usage.output_tokens']), (30, 3))
        self.assertNotIn('Maria', repr(dict(span.attributes)) + repr(span.events))
        self.assertEqual(self.requests_counted(), [('chatbot', 'ok', 1)])

    def test_a_failing_extraction_counts_error_and_logs_only_the_type(self):
        model = MagicMock()
        model.generate_content.side_effect = RuntimeError(f'quota exceeded for {CONVERSATION}')
        with patch('chatbot.ai_utils.genai.GenerativeModel', return_value=model):
            with self.assertLogs('chatbot.ai_utils', 'WARNING') as logs:
                self.assertEqual(AiUtils.extract_preferences_from_conversation(history()), [])
        self.assertEqual(logs.output, ['WARNING:chatbot.ai_utils:preference extraction failed: RuntimeError'])
        span = self.span('gemini generate_content')
        self.assertEqual(span.status.status_code, StatusCode.ERROR)
        self.assertEqual(self.requests_counted(), [('chatbot', 'error', 1)])

    def test_a_failed_whatsapp_send_logs_only_the_type(self):
        error = requests.ConnectionError('HTTPConnectionPool(host=evolution): url: /message/sendText/inst number 5592991234567')
        with patch('chatbot.ai_utils.requests.post', side_effect=error):
            with self.assertLogs('chatbot.ai_utils', 'WARNING') as logs:
                AiUtils.send_whatsapp_message('5592991234567', 'oi Maria')
        self.assertEqual(logs.output, ['WARNING:chatbot.ai_utils:sending a WhatsApp message failed: ConnectionError'])

    def test_a_missing_hairdresser_logs_the_id_only(self):
        with self.assertLogs('chatbot.ai_utils', 'INFO') as logs:
            self.assertIsNone(AiUtils.get_hairdresser_by_id(987654))
        self.assertEqual(logs.output, ['INFO:chatbot.ai_utils:hairdresser 987654 not found'])
