# chatbot/views.py
import requests
import json
import os
import google.generativeai as genai
from datetime import datetime

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from django.conf import settings
from users.models import User, Hairdresser
from users.serializers import UserFullInfoSerializer
from service.models import Service
from reserve.models import Reserve
from reserve.views import get_available_slots
from availability.views import get_hairdresser_availability
from .ai_utils import AiUtils
from .response_messages import ResponseMessage
from .templates import Templates

GEMINI_API_KEY =  settings.GEMINI_API_KEY 
genai.configure(api_key=GEMINI_API_KEY)

# TODO fazer models
user_states = {}
user_chats = {}
user_preferences = {}
recommended_or_searched_hairdressers = {}
chosen_hairdresser = {}
show_services= {}
chosen_service = {}

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

                current_state = user_states.get(sender_number,'start')
                response_message = "Desculpe, não entendi. Poderia repetir?" 
                incoming_text = incoming_text.strip()

                if incoming_text.lower() == ResponseMessage.CHAT_STOP.lower():
                    response_message = ResponseMessage.CHAT_STOPPED
                    user_states.pop(sender_number, None)
                    user_chats.pop(sender_number, None)
                    user_preferences.pop(sender_number,None)
                    AiUtils.send_whatsapp_message(sender_number, response_message)
                    return JsonResponse({"status": "ok"}, status=200)

                if incoming_text.lower() in ['recomendar', 'recomendação', 'sugerir', 'indicar']:
                    if sender_number in user_chats and sender_number in user_preferences:
                        chat_session = user_chats[sender_number]
                        preferences = AiUtils.extract_preferences_from_conversation(chat_session.history)
            
                        if preferences:
                            user_preferences[sender_number] = preferences
                            matching_hairdressers = AiUtils.get_hairdressers_by_preferences(preferences, limit=5)
                            if matching_hairdressers:
                                recommendation_model = AiUtils.create_gemini_model_for_recommendation(matching_hairdressers)
                                recommendation_chat = recommendation_model.start_chat(history=[])
                                recommendation_response = recommendation_chat.send_message(
                                    f"Com base na nossa conversa, preciso de recomendações de cabeleireiros. "
                                    f"Minhas preferências incluem: {', '.join(preferences)}" 
                                )  
                                formatted_answer,names, ids = AiUtils.format_hairdresser(recommendation_response.text)
                                recommended_or_searched_hairdressers[sender_number] = ids
                                response_message = f"Com base no que você me contou, encontrei alguns profissionais perfeitos para você:\n {formatted_answer}"
                                for index in range(len(ids)):
                                    response_message += (
                                        f"\n\n*Digite {index+1}* para visualizar os serviços de {names[index]}"
                                    )  
                                response_message += ( 
                                    f"\n\n*Digite {len(ids)+1}* para buscar profissionais novamente\n\n"
                                ) 

                                user_states[sender_number] = 'hairdresser_service_selection'
                            else:
                                response_message = ("Não encontrei cabeleireiros que correspondam exatamente às suas preferências. "
                                                  "Gostaria que eu amplie a busca ou prefere tentar com outras preferências?")
                        else:
                            response_message = ("Preciso coletar mais informações sobre suas preferências antes de fazer recomendações. "
                                              "Pode me contar mais sobre o que você está procurando?")
                    else:
                        response_message = "Vamos começar nossa conversa primeiro. Que tipo de serviço você está procurando?"
                        user_states[sender_number] = 'collecting_preferences'

                elif current_state == 'start':
                    try:
                        user = User.objects.get(phone=sender_number)
                        response_message = ''
                        response_message += (
                            f"Olá {user.first_name} {user.last_name}! Bem-vindo(a) de volta ao Hairmatch."
                            f"{ResponseMessage.HOW_CAN_I_HELP_YOU_TODAY}"
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
                        f"{ResponseMessage.HOW_CAN_I_HELP_YOU_TODAY}" 
                    )

                    user_states[sender_number] = 'main_menu'

                elif current_state == 'main_menu':
                    if incoming_text == '1':
                        user_states[sender_number] = 'collecting_preferences'
                        preference_model = AiUtils.create_gemini_model_for_preference_collection()
                        chat_session = preference_model.start_chat(history=[])
                        user_chats[sender_number] = chat_session
                        user_preferences[sender_number] = []
                        response_message = ResponseMessage.SERVICE_TYPE_SEARCH
                    elif incoming_text == '2':
                        response_message = ResponseMessage.FIND_SPECIFIC_HAIRDRESSER
                        user_states[sender_number] = 'find_specific_hairdresser'
                    else:
                        response_message = ResponseMessage.INVALID_OPTION_MESSAGE
                elif current_state == 'collecting_preferences':
                    chat_session = user_chats.get(sender_number)
                    if not chat_session:
                        response_message = ResponseMessage.RECOMMENDATION_RESTART_CHAT
                        user_states[sender_number] = 'main_menu'
                    else:
                        try:
                            gemini_response = chat_session.send_message(incoming_text)
                            response_message = gemini_response.text
                            
                            if len(chat_session.history) > 3:  # After some conversation
                                response_message = ResponseMessage.I_COLLECTED_ENOUGH_DATA_RECOMMEND
                                
                        except Exception as e:
                            print(f"Error calling Gemini API: {e}")
                            response_message = ResponseMessage.PROBLEM_WHILE_PROCESSING_OPERATION
                
                elif current_state == 'find_specific_hairdresser':
                    hairdresser_name = incoming_text.lower()
                    try:
                        hairdressers = User.objects.filter(
                            role='hairdresser',
                            first_name__icontains=hairdresser_name
                        ) | User.objects.filter(
                            role='hairdresser',
                            last_name__icontains=hairdresser_name
                        )
                        
                        if hairdressers.exists():
                            serialized_hairdressers = UserFullInfoSerializer(hairdressers, many=True).data
                            response_message = "Encontrei estes profissionais:\n\n"
                            recommended_or_searched_hairdressers[sender_number] = serialized_hairdressers
                            for h in serialized_hairdressers:
                                specialties_str = ", ".join(h['preferences'])
                                response_message += (
                                    f"👤 *{h['first_name']} {h['last_name']}*\n"
                                    f"📍 {h['neighborhood']}, {h['city']}\n"
                                    f"⭐ Nota: {h['rating']}\n"
                                    f"💼 Especialidades: {specialties_str}\n"
                                    f"📝 {h['hairdresser']['resume']}\n\n"
                                )
                        else:
                            response_message = f"Não encontrei nenhum cabeleireiro com o nome '{hairdresser_name}'. Gostaria de tentar outro nome ou receber recomendações baseadas em suas preferências?"
                    except Exception as e:
                        print(f"Error searching for specific hairdresser: {e}")
                        response_message = "Erro ao buscar o cabeleireiro. Tente novamente."
                elif current_state == 'hairdresser_service_selection':
                    try:
                        choice = int(incoming_text) 
                        hairdressers_ids = recommended_or_searched_hairdressers[sender_number]
                        if choice == len(hairdressers_ids)+1:
                            user_states[sender_number] = 'collecting_preferences'
                            response_message = ResponseMessage.SERVICE_TYPE_SEARCH
                        elif hairdressers_ids and 0 < choice <= len(hairdressers_ids):
                            hairdresser_id = hairdressers_ids[choice-1]
                            try: 
                                hairdresser = Hairdresser.objects.get(id=hairdresser_id)
                                chosen_hairdresser[sender_number] = hairdresser_id
                                services = Service.objects.filter(hairdresser=hairdresser)
                                show_services[sender_number] = list(services)
                                if services.exists():
                                    response_message = f"Serviços de {hairdresser.user.first_name} {hairdresser.user.last_name}:\n\n"
                                    for service in services: 
                                        response_message += (
                                            f"*{service.name}*\n"
                                            f"Descrição: {service.description}\n"
                                            f"Preço: R${service.price}\n"
                                            f"Duração: {service.duration} minutos \n\n"
                                        )
                                    response_message += "Qual serviço você gostaria de agendar?\n\n"
                                    for i in range(len(services)):
                                        response_message += f"*Digite {i+1}* para agendar o serviço {services[i].name}\n\n"
                                    response_message += ( 
                                        f"*Digite {len(services)+1}* para buscar profissionais novamente\n\n"
                                    )
                                    user_states[sender_number] = 'service_booking_selection'
                                else:
                                    response_message = "Este profissional ainda não cadastrou serviços."
                                    user_states[sender_number] = 'main_menu'
                            except Hairdresser.DoesNotExist:
                                response_message = "Profissional não encontrado."
                                user_states[sender_number] = 'main_menu'
                        else:
                            response_message = "Opção inválida. Por favor, digite o número correspondente ao profissional."
                    except ValueError:
                        response_message = "Por favor, digite um número."
                    except Exception as e:
                        print(
                            f"Error in hairdresser_service_selection: {e}")
                        response_message = "Ocorreu um erro ao selecionar o profissional. Tente novamente."
                        user_states[sender_number] = 'main_menu'
                
                elif current_state == 'service_booking_selection':
                    choice = int(incoming_text)
                    print(choice)
                    services_list = show_services[sender_number] 
                    if choice == len(services_list)+1:
                        user_states[sender_number] = 'collecting_preferences'
                        response_message = ResponseMessage.SERVICE_TYPE_SEARCH
                    elif services_list and 0 < choice <= len(services_list):
                        service = services_list[choice-1]
                        chosen_service[sender_number] = service.id 
                        hairdresser_id = chosen_hairdresser[sender_number]

                        if not hairdresser_id:
                            response_message = "Erro: não foi possível encontrar o profissional. Vamos começar de novo."
                            user_states[sender_number] = 'main_menu'
                        else:
                            availability_result = get_hairdresser_availability(hairdresser_id=hairdresser_id)
                            print(availability_result)
                            if 'error' in availability_result:
                                response_message = "Não consegui consultar os dias de trabalho deste profissional."
                                user_states[sender_number] = 'main_menu' 
                            else:
                                availabilities = availability_result.get('availabilities', [])
                                if not availabilities:
                                    response_message = "Este profissional ainda não configurou seus dias de trabalho e não pode ser agendado."
                                    user_states[sender_number] = 'main_menu'
                                else:
                                    response_message = f"Ótima escolha! O horário de funcionamento de {service.hairdresser.user.first_name} é:\n\n"
                                    for avail in availabilities:
                                        day_name = Templates.WEEKDAY_TRANSLATIONS.get(avail['weekday'].lower(), avail['weekday'])
                                        start = datetime.strptime(avail['start_time'], '%H:%M:%S').strftime('%H:%M')
                                        end = datetime.strptime(avail['end_time'], '%H:%M:%S').strftime('%H:%M')
                                        response_message += f"*{day_name}:* das {start} às {end}\n"
                                    
                                    response_message += "\nPara qual data você gostaria de agendar?\n"
                                    response_message += "Diga *hoje*, *amanhã* ou use o formato *dd/mm/yyyy*."

                AiUtils.send_whatsapp_message(sender_number,response_message)
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)
        except Exception as e:
            print(f"Error processing webhook: {e}")
            return JsonResponse({"status": "error", "message": "Internal server error"}, status=500)

        return JsonResponse({"status": "ok"}, status=200)
