from flask import Flask, jsonify
import os
from email_notifier import check_emails

app = Flask(__name__)

@app.route('/')
def home():
    return jsonify({
        "status": "running",
        "service": "Email Notifier",
        "email": os.getenv('EMAIL_USER', 'Not configured')
    })

@app.route('/check')
def check():
    """Endpoint para que el cron job ejecute la revisión de emails"""
    try:
        check_emails()
        return jsonify({"status": "success", "message": "Emails checked"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/health')
def health():
    """Health check para mantener el servicio activo"""
    return jsonify({"status": "healthy"})

@app.route('/test-telegram')
def test_telegram():
    """Endpoint para probar la configuración de Telegram"""
    import requests

    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

    # Verificar variables
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return jsonify({
            "status": "error",
            "message": "Variables de entorno no configuradas",
            "missing": {
                "TELEGRAM_BOT_TOKEN": not TELEGRAM_BOT_TOKEN,
                "TELEGRAM_CHAT_ID": not TELEGRAM_CHAT_ID
            }
        }), 400

    # Probar el bot
    try:
        # Verificar bot
        bot_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
        bot_response = requests.get(bot_url, timeout=10)
        bot_result = bot_response.json()

        if not bot_result.get('ok'):
            return jsonify({
                "status": "error",
                "step": "bot_verification",
                "message": "Token inválido",
                "response": bot_result
            }), 401

        bot_info = bot_result.get('result', {})

        # Enviar mensaje de prueba
        send_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        send_data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": "🧪 Test desde Render\n\n✅ Tu configuración de Telegram está funcionando correctamente!",
            "parse_mode": "HTML"
        }

        send_response = requests.post(send_url, data=send_data, timeout=10)
        send_result = send_response.json()

        if send_response.status_code == 200 and send_result.get('ok'):
            return jsonify({
                "status": "success",
                "message": "✅ Configuración de Telegram correcta",
                "bot": {
                    "username": bot_info.get('username'),
                    "id": bot_info.get('id'),
                    "name": bot_info.get('first_name')
                },
                "test_message_sent": True,
                "message_id": send_result.get('result', {}).get('message_id')
            }), 200
        else:
            return jsonify({
                "status": "error",
                "step": "send_message",
                "message": "Error al enviar mensaje",
                "error_code": send_result.get('error_code'),
                "description": send_result.get('description'),
                "response": send_result
            }), 400

    except requests.exceptions.Timeout:
        return jsonify({
            "status": "error",
            "message": "Timeout al conectar con Telegram"
        }), 504
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
