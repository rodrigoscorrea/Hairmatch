import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.test import Client, TestCase
from django.urls import reverse
from opentelemetry.trace import StatusCode

from chatbot.response_messages import ResponseMessage
from chatbot.views import (
    chosen_date, chosen_hairdresser, chosen_service, recommended_or_searched_hairdressers, show_services,
    user_chats, user_preferences, user_states,
)
from hairmatch import testing_telemetry

SENDER = '5592991234567'
TEXT = 'quero luzes como a Maria Silva fez'


def webhook(text):
    return json.dumps({
        'event': 'messages.upsert',
        'data': {'key': {'remoteJid': f'{SENDER}@s.whatsapp.net', 'fromMe': False}, 'message': {'conversation': text}},
    })


def answer(text='Que tipo de luzes?', usage=(40, 5)):
    return SimpleNamespace(
        text=text, usage_metadata=SimpleNamespace(prompt_token_count=usage[0], candidates_token_count=usage[1]),
    )


class ChatbotViewTelemetryTests(testing_telemetry.TelemetryMixin, TestCase):
    """TEL-25 to TEL-27, TEL-41, TEL-42, TEL-58 for the webhook."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.url = reverse('whastapp_chatbot')
        for state in (user_states, user_chats, user_preferences, recommended_or_searched_hairdressers,
                      chosen_hairdresser, show_services, chosen_service, chosen_date):
            state.clear()
            self.addCleanup(state.clear)
        sender = patch('chatbot.views.AiUtils.send_whatsapp_message')
        self.sent = sender.start()
        self.addCleanup(sender.stop)

    def post(self, text):
        return self.client.post(self.url, data=webhook(text), content_type='application/json')

    def requests_counted(self):
        return sorted((a['feature'], a['outcome'], v) for a, v in self.points('hairmatch.ai.requests'))

    def collecting(self, chat):
        user_states[SENDER] = 'collecting_preferences'
        user_chats[SENDER] = chat

    def test_a_chat_turn_is_a_chatbot_gemini_span_with_tokens_and_not_the_message(self):
        chat = MagicMock()
        chat.send_message.return_value = answer()
        chat.history = []
        self.collecting(chat)

        self.assertEqual(self.post(TEXT).status_code, 200)

        span = self.span('gemini generate_content')
        self.assertEqual(span.attributes['hairmatch.ai.feature'], 'chatbot')
        self.assertEqual(span.attributes['gen_ai.usage.input_tokens'], 40)
        self.assertEqual(span.attributes['gen_ai.usage.output_tokens'], 5)
        for private in ('Maria', 'luzes', SENDER):
            self.assertNotIn(private, repr(dict(span.attributes)) + span.name + repr(span.events))
        self.assertEqual(self.requests_counted(), [('chatbot', 'ok', 1)])
        self.assertEqual(sorted((a['feature'], a['direction'], v) for a, v in self.points('hairmatch.ai.tokens')), [('chatbot', 'input', 40), ('chatbot', 'output', 5)])

    def test_a_failed_chat_turn_counts_error_and_logs_only_the_exception_type(self):
        chat = MagicMock()
        chat.send_message.side_effect = RuntimeError(f'429 for {TEXT} from {SENDER}')
        self.collecting(chat)

        with self.assertLogs('chatbot.views', 'WARNING') as logs:
            self.assertEqual(self.post(TEXT).status_code, 200)

        self.assertEqual(logs.output, ['WARNING:chatbot.views:Gemini chat failed: RuntimeError'])
        self.sent.assert_called_once_with(SENDER, ResponseMessage.PROBLEM_WHILE_PROCESSING_OPERATION)
        self.assertEqual(self.span('gemini generate_content').status.status_code, StatusCode.ERROR)
        self.assertEqual(self.requests_counted(), [('chatbot', 'error', 1)])

    def test_the_recommendation_call_is_counted_too(self):
        chat = MagicMock()
        chat.history = []
        self.collecting(chat)
        user_preferences[SENDER] = ['luzes']
        recommendation_chat = MagicMock()
        recommendation_chat.send_message.return_value = answer(text='[]')
        recommendation_model = MagicMock()
        recommendation_model.start_chat.return_value = recommendation_chat
        with patch('chatbot.views.AiUtils.extract_preferences_from_conversation', return_value=['luzes']), \
                patch('chatbot.views.AiUtils.get_hairdressers_by_preferences', return_value=[{'x': 1}]), \
                patch('chatbot.views.AiUtils.create_gemini_model_for_recommendation', return_value=recommendation_model), \
                patch('chatbot.views.AiUtils.format_hairdresser', return_value=('lista', ['Ana'], [1])):
            self.assertEqual(self.post('recomendar').status_code, 200)

        self.assertEqual(self.span('gemini generate_content').attributes['hairmatch.ai.feature'], 'chatbot')
        self.assertEqual(self.requests_counted(), [('chatbot', 'ok', 1)])

    def test_a_failed_name_search_logs_only_the_exception_type(self):
        user_states[SENDER] = 'find_specific_hairdresser'
        with patch('chatbot.views.User.objects.filter', side_effect=RuntimeError(f'syntax error near {TEXT}')):
            with self.assertLogs('chatbot.views', 'WARNING') as logs:
                self.assertEqual(self.post(TEXT).status_code, 200)
        self.assertEqual(logs.output, ['WARNING:chatbot.views:hairdresser search failed: RuntimeError'])
