import requests
from flask import Flask, request, jsonify

# --- Configurações Mínimas ---
EVOLUTION_API_URL = ''
EVOLUTION_API_KEY = ''  # Sua chave da API Evolution
EVOLUTION_INSTANCE_NAME = "hairmatch"  # O nome da sua instância

app = Flask(__name__)


def send_whatsapp_message(number, message):
    """Envia uma mensagem de texto usando a Evolution API."""
    url = f"{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE_NAME}"
    headers = {"apikey": EVOLUTION_API_KEY}
    payload = {
        "number": number,
        "text": message
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        print(f"Resposta '{message}' enviada para {number}")
    except requests.exceptions.RequestException as e:
        print(f"Erro ao enviar mensagem via Evolution API: {e}")


@app.route('/', methods=['POST'])
@app.route('/webhook', methods=['POST'])
def webhook_handler():
    data = request.json
    print(f">>> Webhook Recebido: {data}")

    if (
        data and
        data.get('event') == 'messages.upsert' and
        data.get('data') and
        not data['data'].get('key', {}).get('fromMe')
    ):
        try:
            message_data = data['data']
            sender_jid = message_data['key']['remoteJid']  
            sender_number = sender_jid.split('@')[0]       

            incoming_text = message_data.get('message', {}).get('conversation', '')
            print(f"Mensagem recebida de {sender_number}: {incoming_text}")

            fixed_response = "ola baitola, tudo bem? sou um chatbot simples, estou aqui para te ajudar com o que precisar. Qual é a sua dúvida?"
            send_whatsapp_message(sender_number, fixed_response)

        except Exception as e:
            print(f"Erro ao processar o webhook: {e}")

    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
