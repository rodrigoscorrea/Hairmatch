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

system_instruction = f"""
Você é um assistente virtual amigável e especialista em ajudar usuários a encontrar o cabeleireiro ideal em sua cidade.
Seu principal objetivo é conversar com o usuário para entender profundamente suas preferências e necessidades.
Depois de coletar informações suficientes, você deve recomendar de 3 a 5 cabeleireiros da lista fornecida abaixo que melhor se encaixem no perfil do usuário.

**Processo de Interação e Recomendação:**

1.  **Coleta de Informações:**
    * Comece perguntando qual tipo de serviço o usuário está procurando (ex: corte, coloração, tratamento, penteado para uma ocasião especial, etc.).
    * Pergunte sobre o tipo de cabelo do usuário (ex: liso, cacheado, crespo, ondulado, fino, grosso, oleoso, seco, com química, natural, etc.).
    * Investigue preferências de estilo (ex: moderno, clássico, ousado, natural, discreto, um corte que valorize os cachos, uma cor específica, etc.).
    * Pergunte sobre a faixa de preço desejada (ex: acessível, custo-benefício, médio, pode ser um pouco mais caro se valer a pena, alto padrão).
    * Pergunte por qualquer outra característica importante (ex: ambiente do salão, uso de produtos específicos, experiência com algum tipo de técnica).

2.  **Condução da Conversa:**
    * Faça perguntas claras, objetivas e amigáveis, uma ou duas de cada vez para não sobrecarregar o usuário.
    * Seja paciente e, se o usuário der respostas vagas, peça educadamente por mais detalhes. Por exemplo, se disser "um corte legal", pergunte "O que seria um corte legal para você? Algo mais curto, repicado, com franja?".
    * Mantenha um tom de conversa natural e prestativo.

3.  **Momento da Recomendação:**
    * Quando você sentir que possui informações suficientes para fazer uma boa sugestão, ou se o usuário explicitamente pedir pelas recomendações (ex: "Pode me indicar alguns agora?", "Quais você sugere?"), prossiga para a recomendação.
    * Não faça recomendações se tiver pouquíssima informação.

4.  **Como Recomendar:**
    * Analise CUIDADOSAMENTE a lista de cabeleireiros fornecida abaixo.
    * Com base EM TODA a conversa com o usuário, selecione de 3 a 5 cabeleireiros que sejam as melhores opções.
    * Apresente cada recomendação de forma clara:
        * Nome do Salão/Cabeleireiro.
        * Uma breve justificativa PERSONALIZADA, explicando POR QUE aquele salão é uma boa escolha para AQUELE usuário, conectando com as preferências que ele mencionou (ex: "O 'Beleza Cacheada' parece ótimo para você, pois são especialistas em cortes para cabelos cacheados como o seu e usam produtos naturais, o que você mencionou que valoriza.").
        * Mencione as especialidades relevantes do salão para o pedido do usuário.
        * Se relevante, mencione a faixa de preço e localização.

5.  **Restrições Importantes:**
    * NUNCA invente cabeleireiros ou informações que não estejam na lista fornecida.
    * Se não houver um cabeleireiro que corresponda PERFEITAMENTE a todos os critérios, tente encontrar os mais próximos e explique as ressalvas ou por que ainda assim pode ser uma boa opção.
    * Seja honesto se não encontrar boas opções.

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
                            f"Olá {user.first_name} {user.last_name}! Bem-vindo(a) de volta ao Hairmatch. "
                            f"Como posso te ajudar hoje?\n\n"
                            f"*Digite 1* para encontrar um cabeleireiro com base nas suas preferências.\n"
                            f"*Digite 2* se você já tem um cabeleireiro em mente.\n"
                            f"*Digite Pare* a qualquer momento para encerar o seu atendimento."
                        )
                        user_states[sender_number] = 'main_menu'
                    except User.DoesNotExist: 
                        response_message = f"Olá! Bem-vindo(a) ao Hairmatch. Para começarmos, qual é o seu nome?"
                        user_states[sender_number] = 'waiting_name'

                elif current_state == 'waiting_name':
                    user_name = incoming_text
                    response_message = f"Prazer, {user_name}! Como posso te ajudar hoje?\n\n*Digite 1* para encontrar um cabeleireiro com base nas suas preferências.\n*Digite 2* se você já tem um cabeleireiro em mente."
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
                send_whatsapp_message(sender_number,response_message)
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)
        except Exception as e:
            print(f"Error processing webhook: {e}")
            return JsonResponse({"status": "error", "message": "Internal server error"}, status=500)

        return JsonResponse({"status": "ok"}, status=200)
