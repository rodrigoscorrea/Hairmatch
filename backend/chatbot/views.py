# chatbot/views.py
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from rest_framework.views import APIView
from django.conf import settings

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

                # TODO handle response to the user - gemini and database usage

                response_message = f"Olá, Bem vindo ao Hairmatch, como posso ajudar?"
                send_whatsapp_message(sender_number, response_message)

        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)
        except Exception as e:
            print(f"Error processing webhook: {e}")
            return JsonResponse({"status": "error", "message": "Internal server error"}, status=500)

        return JsonResponse({"status": "ok"}, status=200)
