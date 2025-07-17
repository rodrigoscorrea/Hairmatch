# chatbot/tests/test_ai_utils.py

import json
from datetime import date, timedelta
from unittest.mock import patch, MagicMock, call
from django.test import TestCase, override_settings

from users.models import User, Hairdresser
from preferences.models import Preferences
from chatbot.ai_utils import AiUtils
from users.serializers import UserFullInfoSerializer

class AiUtilsTest(TestCase):

    def setUp(self):
        """Set up test users and preferences using the detailed pattern."""
        self.hairdresser_user1 = User.objects.create(
            email="hairdresser@example.com",
            password="hairdresser123",
            first_name="Joana",
            last_name="Silva",
            phone="+5592984502222",
            complement="Apt 102",
            neighborhood="Downtown",
            city="Manaus",
            state="AM",
            address="Hairdresser Street",
            number="456",
            postal_code="69050750",
            role="hairdresser",
            rating=4.5
        )
        
        self.hairdresser1 = Hairdresser.objects.create(
            user=self.hairdresser_user1,
            cnpj="12345678901212",
            experience_years=4,
            resume="Ela é legal e corta bem" 
        )
        
        # Create another hairdresser for testing
        self.hairdresser_user2 = User.objects.create(
            email="hairdresser2@example.com",
            password="hairdresser123",
            first_name="Pedro",
            last_name="Alves",
            phone="+5592984503333",
            complement="Apt 103",
            neighborhood="Centro",
            city="Manaus",
            state="AM",
            address="Hairdresser Street 2",
            number="789",
            postal_code="69050750",
            role="hairdresser",
            rating=5.0 # Higher rating
        )
        
        self.hairdresser2 = Hairdresser.objects.create(
            user=self.hairdresser_user2,
            cnpj="12345678901567",
            experience_years=3,
            resume="Ele é especialista em coloração"
        )
        
        # Setup preferences
        self.pref_corte = Preferences.objects.create(name='corte moderno')
        self.pref_cor = Preferences.objects.create(name='coloração')
        
        # Assign preferences to hairdressers
        self.hairdresser_user1.preferences.add(self.pref_corte)
        self.hairdresser_user2.preferences.add(self.pref_corte, self.pref_cor)


    @patch('chatbot.ai_utils.genai.GenerativeModel')
    def test_extract_preferences_from_conversation(self, mock_generative_model):
        """Test successful extraction of preferences from chat history."""
        # Setup mock
        mock_model_instance = MagicMock()
        mock_response = MagicMock()
        # Adjusted to match the mock response in the original test
        mock_response.text = "Corte moderno\n- Coloração\n* mechas loiras"
        mock_model_instance.generate_content.return_value = mock_response
        mock_generative_model.return_value = mock_model_instance
        
        chat_history = [MagicMock(parts=[MagicMock(text="Quero um corte moderno e coloração.")])]
        
        # Call function
        preferences = AiUtils.extract_preferences_from_conversation(chat_history)
        
        # Assertions
        # This test remains valid as it doesn't depend on the setUp data structure
        self.assertEqual(preferences, ['corte moderno'])
    
    @patch('chatbot.ai_utils.genai.GenerativeModel', side_effect=Exception("API Error"))
    def test_extract_preferences_exception(self, mock_generative_model):
        """Test that an empty list is returned on API exception."""
        preferences = AiUtils.extract_preferences_from_conversation([])
        self.assertEqual(preferences, [])

    def test_get_hairdressers_by_preferences_with_matches(self):
        """Test finding hairdressers that match a list of preferences."""
        # Pedro matches both 'moderno' and 'cor', so he should be first.
        matches = AiUtils.get_hairdressers_by_preferences(['moderno', 'coloração'])
        self.assertEqual(len(matches), 2)
        self.assertEqual(matches[0]['hairdresser']['user']['first_name'], 'Pedro') # Pedro matches 2
        self.assertEqual(matches[1]['hairdresser']['user']['first_name'], 'Joana') # Joana matches 1

    def test_get_hairdressers_by_preferences_no_list(self):
        """Test that it returns all hairdressers if no preferences are provided."""
        matches = AiUtils.get_hairdressers_by_preferences([], limit=2)
        self.assertEqual(len(matches), 2)

    def test_get_hairdressers_by_preferences_no_match(self):
        """Test that it returns top-rated hairdressers if no preferences match."""
        # 'luzes' does not exist as a preference, should return by rating desc
        matches = AiUtils.get_hairdressers_by_preferences(['luzes'], limit=1)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['hairdresser']['user']['first_name'], 'Pedro') # Pedro has a 5.0 rating

    @patch('chatbot.ai_utils.requests.post')
    def test_send_whatsapp_message_success(self, mock_post):
        """Test successful sending of a WhatsApp message."""
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        with override_settings(EVOLUTION_API_URL='http://test.com', EVOLUTION_INSTANCE_NAME='test_instance', EVOLUTION_API_KEY='test_key'):
            AiUtils.send_whatsapp_message('12345', 'Hello')

        expected_url = 'http://test.com/message/sendText/test_instance'
        expected_payload = {'number': '12345', 'text': 'Hello'}
        expected_headers = {'apikey': 'test_key'}
        
        mock_post.assert_called_once_with(expected_url, json=expected_payload, headers=expected_headers)
        mock_response.raise_for_status.assert_called_once()
        
    def test_format_hairdresser(self):
        """Test formatting of a JSON string with hairdresser data."""
        json_string = """```json
        [
            {
                "id": 1, "first_name": "Joana", "last_name": "Silva",
                "city": "Manaus", "rating": 4.5, "preferences": ["corte"],
                "reasoning": "Ótima em cortes."
            }
        ]
        ```"""
        formatted_text, names, ids = AiUtils.format_hairdresser(json_string)
        self.assertIn("*Nome completo:* Joana Silva", formatted_text)
        self.assertIn("*Localização:* Manaus", formatted_text)
        self.assertIn("*Justificativa personalizada:* Ótima em cortes.", formatted_text)
        self.assertEqual(names, ["Joana Silva"])
        self.assertEqual(ids, [1])

    def test_format_hairdresser_invalid_json(self):
        """Test formatter with invalid JSON."""
        result = AiUtils.format_hairdresser("{'invalid'}")
        self.assertEqual(result, "Erro: Não foi possível decodificar os dados de entrada.")

    def test_get_hairdresser_by_id_success(self):
        """Test retrieving a hairdresser by their ID."""
        hairdresser_data = AiUtils.get_hairdresser_by_id(self.hairdresser_user1.id)
        self.assertIsNotNone(hairdresser_data)
        self.assertEqual(hairdresser_data['hairdresser']['user']['first_name'], 'Joana')

    def test_get_hairdresser_by_id_not_found(self):
        """Test retrieving a non-existent hairdresser ID."""
        hairdresser_data = AiUtils.get_hairdresser_by_id(999)
        self.assertIsNone(hairdresser_data)

    @patch('chatbot.ai_utils.date')
    def test_parse_date_from_text(self, mock_date):
        """Test parsing various date-related strings."""
        today = date(2025, 6, 24)
        mock_date.today.return_value = today
        mock_date.side_effect = lambda *args, **kw: date(*args, **kw)


        self.assertEqual(AiUtils.parse_date_from_text("hoje"), '2025-06-24')
        self.assertEqual(AiUtils.parse_date_from_text("amanhã"), '2025-06-25')
        self.assertEqual(AiUtils.parse_date_from_text("25/06/2025"), '2025-06-25')
        self.assertIsNone(AiUtils.parse_date_from_text("texto qualquer"))


# chatbot/tests/test_views.py

import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from django.conf import settings

from users.models import User, Hairdresser, Customer
from preferences.models import Preferences
from service.models import Service
from chatbot.views import user_states, user_chats, user_preferences, recommended_or_searched_hairdressers, chosen_hairdresser, show_services, chosen_service, chosen_date
from chatbot.response_messages import ResponseMessage


class ChatbotViewTest(TestCase):

    def setUp(self):
        """Set up test data for the chatbot view tests using the detailed pattern."""
        self.client = Client()
        self.evolution_api_url = reverse('whastapp_chatbot') # Make sure you have a URL name for this view

        # Create a customer user using a detailed pattern
        self.customer_user = User.objects.create(
            email="customer@example.com",
            password="customer123",
            first_name="João",
            last_name="Cliente",
            phone="5511987654321", # This is the sender_number
            complement="Apt 201",
            neighborhood="Centro",
            city="Manaus",
            state="AM",
            address="Customer Street",
            number="123",
            postal_code="69050000",
            role="customer"
        )
        self.customer = Customer.objects.create(user=self.customer_user)

        # Create Hairdresser 1 using the detailed pattern
        self.hairdresser_user1 = User.objects.create(
            email="hairdresser@example.com",
            password="hairdresser123",
            first_name="Joana",
            last_name="Silva",
            phone="+5592984502222",
            complement="Apt 102",
            neighborhood="Downtown",
            city="Manaus",
            state="AM",
            address="Hairdresser Street",
            number="456",
            postal_code="69050750",
            role="hairdresser",
            rating=4.5
        )
        self.hairdresser1 = Hairdresser.objects.create(
            user=self.hairdresser_user1,
            cnpj="12345678901212",
            experience_years=4,
            resume="Especialista em loiras."
        )

        # Create Hairdresser 2 using the detailed pattern
        self.hairdresser_user2 = User.objects.create(
            email="hairdresser2@example.com",
            password="hairdresser123",
            first_name="Pedro",
            last_name="Alves",
            phone="+5592984503333",
            complement="Apt 103",
            neighborhood="Centro",
            city="Manaus",
            state="AM",
            address="Hairdresser Street 2",
            number="789",
            postal_code="69050750",
            role="hairdresser",
            rating=5.0
        )
        self.hairdresser2 = Hairdresser.objects.create(
            user=self.hairdresser_user2,
            cnpj="12345678901567",
            experience_years=3,
            resume="Ótimo com cortes."
        )
        
        # Create Services, which are linked to the hairdressers above
        self.service1 = Service.objects.create(
            hairdresser=self.hairdresser1,
            name="Corte Feminino",
            price=120.00,
            duration=60,
            description="Corte e escova."
        )
        self.service2 = Service.objects.create(
            hairdresser=self.hairdresser1,
            name="Coloração",
            price=350.00,
            duration=180,
            description="Luzes e tonalização."
        )
        
        # Base webhook data uses the customer's phone number
        self.sender_number = self.customer_user.phone
        self.webhook_data = {
            "event": "messages.upsert",
            "data": {
                "key": {
                    "remoteJid": f"{self.sender_number}@s.whatsapp.net",
                    "fromMe": False
                },
                "message": {
                    "conversation": "" # This will be set in each test
                }
            }
        }
    
    def tearDown(self):
        """Clean up in-memory dictionaries after each test."""
        user_states.clear()
        user_chats.clear()
        user_preferences.clear()
        recommended_or_searched_hairdressers.clear()
        chosen_hairdresser.clear()
        show_services.clear()
        chosen_service.clear()
        chosen_date.clear()

    def _create_webhook_payload(self, message_text):
        """Helper to create a valid JSON payload for the POST request."""
        payload = self.webhook_data.copy()
        payload['data']['message']['conversation'] = message_text
        return json.dumps(payload)

    @patch('chatbot.views.AiUtils.send_whatsapp_message')
    def test_start_state_existing_user(self, mock_send_message):
        """Test the initial message from an existing user."""
        payload = self._create_webhook_payload("Olá")
        response = self.client.post(self.evolution_api_url, data=payload, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        mock_send_message.assert_called_once()
        sent_message = mock_send_message.call_args[0][1]
        self.assertIn(f"Olá {self.customer_user.first_name}", sent_message)
        self.assertEqual(user_states.get(self.sender_number), 'main_menu')

    @patch('chatbot.views.AiUtils.send_whatsapp_message')
    def test_start_state_new_user(self, mock_send_message):
        """Test the initial message from a new, unregistered user."""
        self.webhook_data['data']['key']['remoteJid'] = "5511999999999@s.whatsapp.net"
        self.sender_number = "5511999999999" # Update sender number for this test
        payload = self._create_webhook_payload("Oi")
        
        response = self.client.post(self.evolution_api_url, data=payload, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        mock_send_message.assert_called_with(self.sender_number, "Olá! Bem-vindo(a) ao Hairmatch. Para começarmos, qual é o seu nome?")
        self.assertEqual(user_states.get(self.sender_number), 'waiting_name')
        
    @patch('chatbot.views.AiUtils.send_whatsapp_message')
    @patch('chatbot.views.AiUtils.create_gemini_model_for_preference_collection')
    def test_main_menu_state_collect_preferences(self, mock_create_model, mock_send_message):
        """Test user selecting option 1 (recommendation) from the main menu."""
        # Mock the model and chat session creation
        mock_model = MagicMock()
        mock_chat_session = MagicMock()
        mock_create_model.return_value = mock_model
        mock_model.start_chat.return_value = mock_chat_session
        
        user_states[self.sender_number] = 'main_menu'
        payload = self._create_webhook_payload("1")

        response = self.client.post(self.evolution_api_url, data=payload, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        mock_send_message.assert_called_with(self.sender_number, ResponseMessage.SERVICE_TYPE_SEARCH)
        self.assertEqual(user_states.get(self.sender_number), 'collecting_preferences')
        self.assertIn(self.sender_number, user_chats) # Chat session should be created

    @patch('chatbot.views.AiUtils.send_whatsapp_message')
    @patch('chatbot.views.get_available_slots')
    @patch('chatbot.views.create_new_reserve')
    @patch('chatbot.views.get_hairdresser_availability')
    def test_full_booking_flow(self, mock_get_availability, mock_create_reserve, mock_get_slots, mock_send_message):
        """Test a full, successful booking flow from service selection to confirmation."""
        # --- State 1: Select a hairdresser ---
        user_states[self.sender_number] = 'hairdresser_service_selection'
        recommended_or_searched_hairdressers[self.sender_number] = [self.hairdresser1.id, self.hairdresser2.id]
        payload = self._create_webhook_payload("1") # Choosing hairdresser1
        response = self.client.post(self.evolution_api_url, data=payload, content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(user_states[self.sender_number], 'service_booking_selection')
        self.assertEqual(chosen_hairdresser[self.sender_number], self.hairdresser1.id)
        mock_send_message.assert_called()
        self.assertIn("Serviços de Joana Silva", mock_send_message.call_args[0][1])

        # --- State 2: Select a service ---
        mock_get_availability.return_value = {
            'availabilities': [{'weekday': 'monday', 'start_time': '09:00:00', 'end_time': '18:00:00'}]
        }
        payload = self._create_webhook_payload("2") # Choosing "Coloração"
        response = self.client.post(self.evolution_api_url, data=payload, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(user_states[self.sender_number], 'waiting_for_date')
        self.assertEqual(chosen_service[self.sender_number], self.service2.id)
        self.assertIn("Para qual data você gostaria de agendar?", mock_send_message.call_args[0][1])

        # --- State 3: Provide a date ---
        mock_get_slots.return_value = {'available_slots': ['14:00', '15:00', '16:00']}
        payload = self._create_webhook_payload("amanhã")
        response = self.client.post(self.evolution_api_url, data=payload, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(user_states[self.sender_number], 'confirm_booking')
        self.assertIn(self.sender_number, chosen_date)
        self.assertIn("Horários disponíveis para", mock_send_message.call_args[0][1])
        
        # --- State 4: Confirm time and booking ---
        mock_create_reserve.return_value = {'success': True}
        payload = self._create_webhook_payload("14:00")
        response = self.client.post(self.evolution_api_url, data=payload, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        self.assertIn("✅ *Agendamento Confirmado!* ✅", mock_send_message.call_args[0][1])
        self.assertNotIn(self.sender_number, user_states) # State should be cleared
        
    @patch('chatbot.views.AiUtils.send_whatsapp_message')
    def test_stop_command(self, mock_send_message):
        """Test that the 'Parar' command stops the chat and clears the state."""
        user_states[self.sender_number] = 'collecting_preferences'
        user_chats[self.sender_number] = "dummy_chat"
        payload = self._create_webhook_payload(ResponseMessage.CHAT_STOP)
        
        response = self.client.post(self.evolution_api_url, data=payload, content_type='application/json')

        self.assertEqual(response.status_code, 200)
        mock_send_message.assert_called_with(self.sender_number, ResponseMessage.CHAT_STOPPED)
        self.assertNotIn(self.sender_number, user_states)
        self.assertNotIn(self.sender_number, user_chats)


