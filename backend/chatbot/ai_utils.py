import logging
import requests
import json
import re
import google.generativeai as genai
from datetime import datetime, date, timedelta

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from hairmatch import telemetry
from users.models import User
from users.serializers import UserFullInfoSerializer
from .prompts import Prompts
from .templates import Templates

logger = logging.getLogger(__name__)

GEMINI_MODEL = 'gemini-2.0-flash'


class AiUtils():
    @staticmethod
    def extract_preferences_from_conversation(chat_history):
        """
        Extract preferences from the conversation using Gemini
        Returns a list of preferences
        """
        try:
            # Create a specialized model for preference extraction
            extraction_prompt = Prompts.EXTRACTION_PROMPT
            
            extraction_model = genai.GenerativeModel(
                GEMINI_MODEL,
                system_instruction=extraction_prompt
            )
            
            # Convert chat history to text
            conversation_text = ""
            for message in chat_history:
                if hasattr(message, 'parts'):
                    for part in message.parts:
                        conversation_text += f"{part.text}\n"
            
            with telemetry.gemini_call('chatbot', GEMINI_MODEL) as call:
                response = extraction_model.generate_content(
                    f"Conversa para análise:\n{conversation_text}"
                )
                call.record_usage(response)
            
            # Parse the response to extract preferences
            preferences = []
            if response.text:
                lines = response.text.strip().split('\n')
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('-') and not line.startswith('*'):
                        preferences.append(line.lower())
            
            return preferences[:10]  # Limit to 10 preferences max
            
        except Exception as e:
            # Only the type: the exception text can quote the conversation.
            logger.warning('preference extraction failed: %s', type(e).__name__)
            return []

    @staticmethod
    def format_hairdressers_for_prompt(h_list):
        formatted_list = "\nAqui está a lista de cabeleireiros disponíveis para sua referência:\n"
        for h in h_list:
            specialties_str = ", ".join(h['preferences'])
            formatted_list += (
                f"- Nome: {h['first_name']}\n"
                f"  Sobrenome: {h['last_name']}\n"
                f"  Descrição: {h['hairdresser']['resume']}\n"
                f"  Especialidades: {specialties_str}\n"
                f"  Localização: {h['neighborhood'], h['city']}\n"
                f"  Nota: {h['rating']}\n"
            )
        return formatted_list

    @staticmethod
    def get_hairdressers_by_preferences(preferences_list, limit=5):
        """
        Advanced version that scores hairdressers based on how many preferences they match
        """
        try:
            from preferences.models import Preferences 
            from django.db.models import Q, Count 
            
            if not preferences_list:
                return UserFullInfoSerializer(
                    User.objects.filter(role='hairdresser', is_active=True)[:limit], 
                    many=True
                ).data
        
            preference_queries = Q()
            for preference in preferences_list:
                preference_queries |= Q(name__icontains=preference)
            
            matching_preferences = Preferences.objects.filter(preference_queries)
            if not matching_preferences.exists():
                logger.info('no preference matched, offering the top-rated hairdressers')
                return UserFullInfoSerializer(
                    User.objects.filter(role='hairdresser', is_active=True).order_by('-rating')[:limit], 
                    many=True
                ).data
            
            matching_hairdressers = User.objects.filter(
                role='hairdresser',
                is_active=True,
                preferences__in=matching_preferences
            ).annotate(
                preference_match_count=Count('preferences', filter=Q(preferences__in=matching_preferences))
            ).order_by('-preference_match_count', '-rating')[:limit]
            
            return UserFullInfoSerializer(matching_hairdressers, many=True).data
            
        except Exception as e: 
            return UserFullInfoSerializer(
                User.objects.filter(role='hairdresser', is_active=True)[:limit], 
                many=True
            ).data

    @staticmethod
    def create_gemini_model_for_preference_collection():
        """Create Gemini model for collecting user preferences"""
        return genai.GenerativeModel(
            GEMINI_MODEL,
            system_instruction=Prompts.PREFERENCE_COLLECTION_PROMPT,
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 1024
            }
        )

    @staticmethod
    def create_gemini_model_for_recommendation(hairdressers_list):
        """Create Gemini model for making recommendations with specific hairdressers"""
        system_instruction = Prompts.RECOMMENDATION_PROMPT + f"""
        **Lista de Cabeleireiros Disponíveis:**
        {hairdressers_list}
        """

        return genai.GenerativeModel(
            GEMINI_MODEL,
            system_instruction=system_instruction,
            generation_config={
                "temperature": 0.65,
                "max_output_tokens": 2048
            }
        )

    @staticmethod
    def send_whatsapp_message(number, message):
        url = f"{settings.EVOLUTION_API_URL}/message/sendText/{settings.EVOLUTION_INSTANCE_NAME}"
        headers = {"apikey": settings.EVOLUTION_API_KEY}
        payload = {
            "number": number,
            "text": message
        }
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()

        except requests.exceptions.RequestException as e:
            # Only the type: the text of the error carries the URL and the number it was sent to.
            logger.warning('sending a WhatsApp message failed: %s', type(e).__name__)

    @staticmethod
    def format_hairdresser(text):
        
        new_text = text.strip().strip('"').strip()
        new_text = re.sub(r'```json|```', '', new_text).strip()


        try:
            hairdressers_data = json.loads(new_text) 
        except json.JSONDecodeError:
            return "Erro: Não foi possível decodificar os dados de entrada."
        
        hairdressers_formatted = ""
        names = []
        ids = []

        for h in hairdressers_data:
            ids.append(h['id'])
            fullname = f"{h['first_name']} {h['last_name']}"
            names.append(fullname)
            location = h['city']
            rating = h['rating']
            preferences =  ', '.join(h['preferences'])
            reasoning = h['reasoning']
        
            hairdressers_formatted += f"""\n- 👤 *Nome completo:* {fullname}\n- 📍 *Localização:* {location}\n- ⭐ *Avaliação:* {rating}\n- 💼 *Especialidades relevantes:* {preferences}\n- ✨ *Justificativa personalizada:* {reasoning}"""

        return hairdressers_formatted.strip(), names, ids
    
    @staticmethod
    def get_hairdresser_by_id(hairdresser_id):
        try:
            hairdresser = User.objects.get(id=hairdresser_id, role='hairdresser')
            return UserFullInfoSerializer(hairdresser).data
            
        except ObjectDoesNotExist:
            logger.info('hairdresser %s not found', hairdresser_id)
            return None
        except Exception as e:
            logger.warning('fetching hairdresser %s failed: %s', hairdresser_id, type(e).__name__)
            return None
    
    @staticmethod
    def parse_date_from_text(text):
        text = text.lower()
        today = date.today()
        if 'hoje' in text:
            return today.strftime('%Y-%m-%d')
        if 'amanhã' in text:
            tomorrow = today + timedelta(days=1)
            return tomorrow.strftime('%Y-%m-%d')
        try:
            # Try to parse 'DD/MM/YYYY'
            dt = datetime.strptime(text, '%d/%m/%Y')
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            return None
