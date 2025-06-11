# chatbot/views.py
import requests
import json
import os
import google.generativeai as genai

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from django.conf import settings
from users.models import User
from users.serializers import UserFullInfoSerializer
from .prompts import RECOMENDATION_PROMPT
from .response_messages import HAIRDRESSER_NOT_FOUND, HOW_CAN_I_HELP_YOU_TODAY

GEMINI_API_KEY =  settings.GEMINI_API_KEY 
genai.configure(api_key=GEMINI_API_KEY)

# TODO mudar para acessar o banco
user_states = {}
#armazena a sessão do gemini por usuário
user_chats = {}
hairdressers_list = UserFullInfoSerializer(
    User.objects.filter(role='hairdresser')[:10], 
    many=True
).data


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

system_instruction = RECOMENDATION_PROMPT + f"""
**Lista de Cabeleireiros Disponíveis:**
{format_hairdressers_for_prompt(hairdressers_list)}
"""

gemini_model = genai.GenerativeModel(
    'gemini-2.0-flash',
    system_instruction=system_instruction,
    generation_config={
        "temperature": 0.65,
        "max_output_tokens": 2048
    }
)

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
        print(f"Error sending message via Evolution API: {e}")

class EvolutionApi(APIView):
    def post(self, request):
        try:
            data = json.loads(request.body)
            
            if (data.get('event') == 'messages.upsert' and not data.get('data', {}).get('key', {}).get('fromMe')):
                message_data = data['data']
                sender_jid = message_data['key']['remoteJid']
                sender_number = sender_jid.split('@')[0]
                incoming_text = message_data.get('message', {}).get('conversation', '')
                if not incoming_text:
                    return JsonResponse({"status":"ok", "message":"No text in message"}, status=200)


                # TODO handle response to the user - gemini and database usage
                current_state = user_states.get(sender_number,'start')
                response_message = "Desculpe, não entendi. Poderia repetir?" 
                incoming_text = incoming_text.strip()

                if incoming_text.lower() == 'pare':
                    response_message = "Atendimento finalizado. Obrigado por conversar comigo!"
                    user_states.pop(sender_number, None)
                    user_chats.pop(sender_number, None)
                    send_whatsapp_message(sender_number, response_message)
                    return JsonResponse({"status": "ok"}, status=200)

                if current_state == 'start':
                    try:
                        user = User.objects.get(phone=sender_number)
                        response_message = ''
                        response_message += (
                            f"Olá {user.first_name} {user.last_name}! Bem-vindo(a) de volta ao Hairmatch."
                            f"{HOW_CAN_I_HELP_YOU_TODAY}"
                        )
                        user_states[sender_number] = 'main_menu'
                    except User.DoesNotExist: 
                        response_message = f"Olá! Bem-vindo(a) ao Hairmatch. Para começarmos, qual é o seu nome?"
                        user_states[sender_number] = 'waiting_name'

                elif current_state == 'waiting_name':
                    user_name = incoming_text
                    response_message=''
                    response_message += (
                        f"Prazer, {user_name}!"
                        f"{HOW_CAN_I_HELP_YOU_TODAY}" 
                    )

                    user_states[sender_number] = 'main_menu'

                elif current_state == 'main_menu':
                    if incoming_text == '1':
                        user_states[sender_number] = 'gemini_recommendation'
                        chat_session = gemini_model.start_chat(history=[])
                        user_chats[sender_number] = chat_session
                        response_message = "Ótimo! Para começar, me diga: que tipo de serviço você está buscando hoje? (ex: corte, coloração, um tratamento especial...)"
                    elif incoming_text == '2':
                        response_message = "Entendido. Qual o nome do cabeleireiro que você procura?"
                        user_states[sender_number] = 'find_specific_hairdresser'
                    else:
                        response_message = "Opção inválida. Por favor, digite '1' para recomendações ou '2' para buscar um profissional específico."
                elif current_state == 'gemini_recommendation':
                    chat_session = user_chats.get(sender_number)
                    if not chat_session:
                        response_message = "Opa! Parece que nossa conversa foi interrompida. Vamos recomeçar. Digite '1' para receber recomendações."
                        user_states[sender_number] = 'main_menu'
                    else:
                        try:
                            gemini_response = chat_session.send_message(incoming_text)
                            response_message = gemini_response.text
                        except Exception as e:
                            print(f"Error calling Gemini API: {e}")
                            response_message = "Desculpe, estou com um problema para processar sua solicitação no momento. Tente novamente em alguns instantes."
                elif current_state == 'find_specific_hairdresser':
                    try:
                        user = User.objects.get(first_name=incoming_text)
                        user_data = UserFullInfoSerializer(user).data
                        response_message=f'Apresentando profissional {user_data}'
                    except User.DoesNotExist:
                        response_message=HAIRDRESSER_NOT_FOUND
                send_whatsapp_message(sender_number,response_message)
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)
        except Exception as e:
            print(f"Error processing webhook: {e}")
            return JsonResponse({"status": "error", "message": "Internal server error"}, status=500)

        return JsonResponse({"status": "ok"}, status=200)
